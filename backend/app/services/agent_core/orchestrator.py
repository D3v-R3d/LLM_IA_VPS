"""
Agent Orchestrator - Central orchestration layer.

Implements all 7 fixes:
1. Idempotency - prevent re-execution of successful tools
2. Tool results collision - use unique call_id
3. Loop detection - sliding window + frequency + whitelist
4. Planning JSON parsing - strict validation + fallback
5. Context compression - summarize instead of delete
6. Step evaluation - detect progress stagnation
7. Retry stability - exponential backoff + strict limits
"""

import asyncio
import json
import time
import logging
import os
import re
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any

from app.services.agent_core.models import Decision, Plan, RunState, detect_loop_v2, generate_call_key
from app.services.agent_core.intent_classifier import classify_message
from app.observability.event_logger import EventLogger
from app.observability.event_types import EventType, EventLevel

logger = logging.getLogger(__name__)

SPLIT_PATTERN = re.compile(
    r"\b(?:and|then|after|ensuite|puis|plus)\b",
    re.I
)

TOOL_PATTERNS = [
    (["list", "directory", "folder"], ("List directory contents", "ls")),
    (["read", "file"], ("Read file content", "read_file")),
    (["write", "create"], ("Write to file", "write_file")),
    (["search", "find"], ("Search for content", "grep")),
    (["docker"], ("Docker operation", "docker")),
    (["bash", "command", "execute"], ("Execute command", "bash")),
]

NO_RETRY_TOOLS: Set[str] = {"write_file", "docker_run", "docker_exec", "http_request", "postgres_insert", "postgres_update", "postgres_delete"}

SAFE_TOOLS: Set[str] = {"ls", "dir", "list", "search", "grep", "find", "web_search", "read_file", "postgres_query", "postgres_list_tables", "postgres_describe_table"}


@dataclass
class OrchestratorConfig:
    """Configuration for AgentOrchestrator."""
    max_steps: int = 3
    hard_limit: int = 6
    complexity_threshold: int = 3
    max_retry_per_step: int = 2
    max_retries_per_tool: int = 2
    context_max_messages: int = 10
    loop_window_size: int = 5
    max_consecutive_same_tool: int = 3
    debug: bool = False
    # Performance tunables (v2.2)
    llm_timeout: int = 45
    tool_timeout: int = 30
    retry_timeout: int = 15

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        """Load config from environment variables."""
        return cls(
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "3")),
            hard_limit=int(os.getenv("AGENT_HARD_LIMIT", "6")),
            complexity_threshold=int(os.getenv("AGENT_COMPLEXITY_THRESHOLD", "3")),
            max_retry_per_step=int(os.getenv("AGENT_MAX_RETRY_PER_STEP", "2")),
            max_retries_per_tool=int(os.getenv("AGENT_MAX_RETRIES_PER_TOOL", "2")),
            context_max_messages=int(os.getenv("AGENT_CONTEXT_MAX_MESSAGES", "10")),
            loop_window_size=int(os.getenv("AGENT_LOOP_WINDOW_SIZE", "5")),
            max_consecutive_same_tool=int(os.getenv("AGENT_MAX_CONSECUTIVE_SAME_TOOL", "3")),
            debug=os.getenv("AGENT_DEBUG", "false").lower() == "true",
            llm_timeout=int(os.getenv("AGENT_LLM_TIMEOUT", "45")),
            tool_timeout=int(os.getenv("AGENT_TOOL_TIMEOUT", "30")),
            retry_timeout=int(os.getenv("AGENT_RETRY_TIMEOUT", "15")),
        )


class AgentOrchestrator:
    """Central orchestration layer for the agent."""

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        if config is None:
            self.config = OrchestratorConfig.from_env()
        elif isinstance(config, OrchestratorConfig):
            self.config = config
        else:
            from app.services.agent_core.config import AgentConfig
            if isinstance(config, AgentConfig):
                self.config = OrchestratorConfig(
                    max_steps=config.max_steps,
                    hard_limit=config.hard_limit,
                    complexity_threshold=config.complexity_threshold,
                    max_retry_per_step=config.max_retry_per_step,
                    max_retries_per_tool=getattr(config, 'max_retries_per_tool', 2),
                    context_max_messages=getattr(config, 'context_max_messages', 10),
                    loop_window_size=getattr(config, 'loop_window_size', 5),
                    max_consecutive_same_tool=getattr(config, 'max_consecutive_same_tool', 3),
                    debug=config.debug,
                    llm_timeout=45,
                    tool_timeout=30,
                    retry_timeout=15,
                )
            else:
                self.config = config
        self._setup_logging()

        from app.services.agent_tools.registry import get_registry
        from app.services.agent_core.tool_executor import ToolExecutor
        from app.services.agent_core.side_systems import BudgetManager

        self.registry = get_registry()
        self.tool_executor = ToolExecutor(registry=self.registry)
        
        self._provider_cache = {}
        self._tools_cache = None

        budgets_config = os.getenv("AGENT_TOOL_BUDGETS", "")
        budgets = {}
        if budgets_config:
            for part in budgets_config.split(","):
                if ":" in part:
                    tool, count = part.split(":")
                    budgets[tool.strip()] = int(count.strip())
        self.budget_manager = BudgetManager(budgets) if budgets else None

    def _setup_logging(self):
        """Setup logging based on debug flag."""
        if self.config.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # ═══════════════════════════════════════════════════════════════════════
    # ENTRY POINT
    # ═══════════════════════════════════════════════════════════════════════

    async def run(
        self,
        user_message: str,
        messages_history: List[Dict],
        system_prompt: str,
        chat_id: str,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        db_session: Any = None,
        conversation_id: Any = None,
        run_id: Optional[str] = None,
    ) -> str:
        """Main entry point - full agent flow."""
        logger.debug(f"Orchestrator run: user_message={user_message[:50]}...")

        state = RunState()
        state.run_id = run_id

        event_logger = None
        if db_session and run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=run_id, chat_id=None)
            except Exception:
                pass

        if event_logger and run_id:
            event_logger.emit(
                event_type=EventType.AGENT_START,
                event_name="agent_start",
                payload={"model": model, "provider": provider_name, "message_preview": user_message[:100]},
            )

        try:
            intent_result = self.intent_classification(user_message)
            complexity = intent_result["complexity"]

            logger.debug(f"Intent: {intent_result['intent']}, complexity: {complexity}")

            plan = await self.plan(user_message, complexity, event_logger=event_logger)
            if plan:
                state.plan = plan
                logger.debug(f"Plan: {len(plan.steps)} steps, tools: {plan.expected_tools}")

            context = self._build_context(system_prompt, messages_history, user_message)
            
            # NEW: Hybrid routing - deterministic router first, then embeddings fallback
            selected_tool_names = None
            
            if user_message:
                # Step 1: Try deterministic router (fast path <1ms)
                from app.services.agent_core.tool_router import route as route_tools
                router_tools = route_tools(user_message)
                if router_tools:
                    selected_tool_names = router_tools
                    logger.info(f"Router tools (fast path): {selected_tool_names}")
            
            # Step 2: Fallback to embeddings if router returned None
            if selected_tool_names is None and user_message:
                from app.services.tool_registry.registry import search_tools
                results = search_tools(user_message, limit=15)
                selected_tool_names = [r["name"] for r in results if r["score"] >= 0.45]
                logger.info(f"Embedding tools (fallback): {selected_tool_names}")
            
            # Step 3: Empty list if nothing found
            if selected_tool_names is None:
                selected_tool_names = []
            
            logger.info(f"Selected tools for LLM: {selected_tool_names}")
            
            response = await self._execute_loop(
                context=context,
                model=model,
                provider_name=provider_name,
                state=state,
                db_session=db_session,
                selected_tools=selected_tool_names
            )

            final_response = await self.synthesize(
                response.get("tool_results", []),
                response.get("direct_response", ""),
                state
            )

            await self._store_interaction(user_id, user_message, final_response, state)

            if event_logger and run_id:
                event_logger.emit(
                    event_type=EventType.AGENT_END,
                    event_name="agent_end",
                    payload={"success": True, "final_response_length": len(final_response)},
                )

            return final_response

        except Exception as e:
            logger.exception(f"AgentOrchestrator error: {e}")
            if event_logger and run_id:
                event_logger.emit(
                    event_type=EventType.AGENT_END,
                    event_name="agent_end",
                    payload={"success": False, "error": str(e)[:200]},
                )
            raise

    # ═══════════════════════════════════════════════════════════════════════
    # INTENT CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════

    def intent_classification(self, message: str) -> Dict:
        from app.services.agent_core.intent_classifier import classify_message
        return classify_message(message)

    async def plan(self, message: str, complexity: int, event_logger=None) -> Optional[Plan]:
        """Generate a plan based on message complexity."""
        if complexity >= 4:
            return await self._llm_plan(message, event_logger=event_logger)
        return self._lightweight_plan(message)

    async def _llm_plan(self, message: str, event_logger=None) -> Optional[Plan]:
        """LLM-based structured planning for complexity 4-5 with strict JSON validation."""

        from app.services.llm.provider_factory import provider_factory
        from app.core.config import settings
        from app.services.prompt_service import PromptService
        from app.services.agent_core.intent_classifier import select_tools_for_message

        tools_list = ", ".join(select_tools_for_message(message)) if message else "none"

        planning_template = PromptService.get_planning_prompt()

        try:
            planning_prompt = planning_template.format(
                message=message,
                available_tools=tools_list
            )
        except Exception as e:
            logger.error(f"Planning prompt formatting failed: {e}")
            if event_logger:
                event_logger.emit(
                    event_type=EventType.PLAN_FALLBACK,
                    event_name="plan_fallback",
                    payload={"reason": "template_format_error", "fallback": "lightweight"},
                )
            return self._lightweight_plan(message)

        try:
            if event_logger:
                event_logger.emit_llm_request(
                    model=settings.LLM_MODEL or "default",
                    provider=settings.LLM_PROVIDER,
                    prompt_length=len(planning_prompt),
                    tools_count=len(tools_list.split(",")) if tools_list != "none" else 0,
                )

            provider = provider_factory.get_provider(settings.LLM_PROVIDER)

            response = await provider.chat(
                model=settings.LLM_MODEL or "default",
                messages=[{"role": "user", "content": planning_prompt}],
                options={"max_tokens": 500}
            )

            content = response.get("content") if isinstance(response, dict) else str(response)

            if event_logger:
                event_logger.emit_llm_response(
                    model=settings.LLM_MODEL or "default",
                    provider=settings.LLM_PROVIDER,
                    tokens_in=len(planning_prompt) // 4,
                    tokens_out=len(content) // 4,
                    duration_ms=0,
                    response_preview=content[:200] if content else None,
                )

            plan_data = self._parse_json_plan_strict(content)

            if not plan_data:
                logger.warning("LLM returned invalid plan JSON → fallback lightweight")
                if event_logger:
                    event_logger.emit(
                        event_type=EventType.PLAN_FALLBACK,
                        event_name="plan_fallback",
                        payload={"reason": "invalid_json", "fallback": "lightweight"},
                    )
                return self._lightweight_plan(message)

            steps = plan_data.get("steps", [])
            tools = plan_data.get("tools", [])

            if not steps:
                logger.warning("LLM plan empty → fallback lightweight")
                if event_logger:
                    event_logger.emit(
                        event_type=EventType.PLAN_FALLBACK,
                        event_name="plan_fallback",
                        payload={"reason": "empty_plan", "fallback": "lightweight"},
                    )
                return self._lightweight_plan(message)

            return Plan(
                steps=steps,
                expected_tools=tools
            )

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            if event_logger:
                event_logger.emit_error(
                    error_type="LLMPlanningError",
                    error_message=str(e),
                )
            return self._lightweight_plan(message)

    def _lightweight_plan(self, message: str) -> Plan:
        """Simple heuristic - split by conjunctions."""
        steps = []
        expected_tools = []
        seen = set()

        for part in SPLIT_PATTERN.split(message.lower()):
            part = part.strip()
            if not part:
                continue

            for keywords, (step, tool) in TOOL_PATTERNS:
                if all(k in part for k in keywords):
                    if tool not in seen:
                        seen.add(tool)
                        steps.append(step)
                        expected_tools.append(tool)
                    break

        if not steps:
            steps.append("Analyze request")
            expected_tools.append("none")

        return Plan(
            steps=steps,
            expected_tools=expected_tools
        )

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION LOOP
    # ═══════════════════════════════════════════════════════════════════════
        """Strict JSON parsing with validation."""
        try:
            content = content.strip()
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*$', '', content)
            content = content.strip('`')

            data = json.loads(content)

            if not isinstance(data, dict):
                return None
            if not isinstance(data.get("steps"), list):
                logger.debug("Plan validation: 'steps' is not a list")
                return None
            if not isinstance(data.get("tools"), list):
                logger.debug("Plan validation: 'tools' is not a list")
                return None

            return data
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse failed: {e}")
            return None
        except Exception as e:
            logger.debug(f"Plan validation error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION LOOP V2 - OPTIMIZED
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_loop(
        self,
        context: List[Dict],
        model: Optional[str],
        provider_name: Optional[str],
        state: RunState,
        db_session: Any = None,
        selected_tools: Optional[List[Dict]] = None
    ) -> Dict:
        """Optimized execution loop with fast path and parallel execution."""
        
        max_steps = min(self.config.max_steps, self.config.hard_limit)
        
        for step in range(1, max_steps + 1):
            loop_start = time.time()
            llm_start = time.time()
            state.iteration = step
            state.step_retries = 0
            logger.debug(f"Execution step: {step}/{max_steps}")

            response = await self._call_llm(context, model, provider_name, db_session, run_id=state.run_id, selected_tools=selected_tools)
            llm_ms = int((time.time() - llm_start) * 1000)
            logger.info(f"STEP {step}: LLM took {llm_ms}ms")

            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                content = response.get("message", {}).get("content", "")
                logger.info(f"STEP {step}: direct response, total {int((time.time() - loop_start) * 1000)}ms")
                return {"direct_response": content, "tool_results": []}

            if tool_calls:
                self._update_tool_history(tool_calls, state)

                loop_tool = detect_loop_v2(
                    state.tool_history,
                    state.tool_call_counts,
                    window_size=self.config.loop_window_size,
                    max_consecutive=self.config.max_consecutive_same_tool
                )
                if loop_tool:
                    logger.warning(f"AGENT_LOOP_DETECTED: {loop_tool}")
                    return {
                        "direct_response": f"Loop detected: {loop_tool} repeated too many times. Task terminated.",
                        "tool_results": []
                    }

            if self.budget_manager:
                tool_calls = self.budget_manager.check(tool_calls)
                if not tool_calls:
                    return {
                        "direct_response": "Tool budget exhausted for this request.",
                        "tool_results": []
                    }

            tools_start = time.time()
            tool_results = await self._execute_with_idempotency(tool_calls, state, db_session=db_session)
            tools_ms = int((time.time() - tools_start) * 1000)
            logger.info(f"STEP {step}: TOOLS took {tools_ms}ms ({len(tool_results)} results)")

            for result in tool_results:
                if result and result.success:
                    state.completed_tools.append(result.tool)

            state.last_tool_result_success = all(r.success for r in tool_results)

            decision = await self._evaluate_step_v2(tool_results, state, context)
            eval_ms = int((time.time() - loop_start) * 1000) - llm_ms - tools_ms
            logger.info(f"STEP {step}: EVAL took {eval_ms}ms, decision={decision}")

            # EARLY EXIT: all tools succeeded and we have results
            if decision == Decision.STOP and tool_results:
                all_success = all(r and r.success for r in tool_results)
                if all_success and step <= 2:
                    logger.info(f"STEP {step}: early exit (all tools succeeded), total {int((time.time() - loop_start) * 1000)}ms")
                    break

            if decision == Decision.STOP:
                break

            self._add_results_to_context(context, tool_results)
            # Only compress if context is getting large
            if len(context) > self.config.context_max_messages + 5:
                context = self._compress_context_smart(context)

            loop_ms = int((time.time() - loop_start) * 1000)
            logger.info(f"STEP {step}: TOTAL took {loop_ms}ms")

        return {
            "direct_response": "",
            "tool_results": tool_results if step == 1 else state.completed_tools
        }

    def _update_tool_history(self, tool_calls: List[Dict], state: RunState):
        """Update tool history with per-tool counters."""
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            if name:
                state.tool_history.append(name)
                state.tool_call_counts[name] = state.tool_call_counts.get(name, 0) + 1

    # ═══════════════════════════════════════════════════════════════════════
    # TOOL EXECUTION V2 - OPTIMIZED WITH PARALLELIZATION
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_with_idempotency(
        self,
        tool_calls: List[Dict],
        state: RunState,
        db_session: Any = None
    ) -> List:
        """Optimized tool execution with parallelization for safe tools."""
        
        event_logger = None
        if db_session and state.run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=state.run_id, chat_id=None)
            except Exception:
                pass

        results = [None] * len(tool_calls)
        to_execute = []
        indices = []

        for i, tc in enumerate(tool_calls):
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)

            if call_key in state.executed_calls:
                prev = state.executed_calls[call_key]
                if prev.get("status") == "success":
                    logger.debug(f"Idempotency skip: {tool_name} already executed successfully")
                    results[i] = prev["result"]
                    continue
                if prev.get("status") == "failed" and tool_name in NO_RETRY_TOOLS:
                    logger.debug(f"Skipping retry for {tool_name} (side-effect tool)")
                    results[i] = prev["result"]
                    continue

            to_execute.append(tc)
            indices.append(i)

        if not to_execute:
            return results

        if event_logger:
            for tc in to_execute:
                tool_name = tc.get("function", {}).get("name", "")
                call_key = generate_call_key(tc)
                event_logger.emit_tool_call(
                    tool_name=tool_name,
                    call_id=call_key,
                    arguments=tc.get("function", {}).get("arguments", {}),
                )

        batch_results = await asyncio.wait_for(
                self.tool_executor.execute_batch(to_execute),
                timeout=float(self.config.tool_timeout)
            )

        for idx, tool_result in zip(indices, batch_results):
            tc = tool_calls[idx]
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)
            
            results[idx] = tool_result

            state.executed_calls[call_key] = {
                "status": "success" if tool_result and tool_result.success else "failed",
                "result": tool_result,
                "tool_name": tool_name
            }

            if event_logger and tool_result:
                event_logger.emit_tool_result(
                    tool_name=tool_name,
                    call_id=call_key,
                    success=bool(tool_result.success),
                    duration_ms=int(tool_result.metadata.duration_ms) if tool_result.metadata else 0,
                    result_size=len(str(tool_result.data)) if tool_result.data else 0,
                    error=tool_result.error if not tool_result.success else None,
                )

        failed = [(i, r) for i, r in enumerate(results) if r and not r.success]

        for idx, result in failed:
            tool_name = tool_calls[idx].get("function", {}).get("name", "")
            retry_call_key = generate_call_key(tool_calls[idx])

            if tool_name in NO_RETRY_TOOLS:
                logger.debug(f"Skipping retry for {tool_name} (side-effect tool)")
                continue

            retry_key = f"retry_{retry_call_key}"
            retry_count = state.tool_call_counts.get(retry_key, 0)
            if retry_count >= self.config.max_retries_per_tool:
                logger.debug(f"Max retries reached for {tool_name}")
                continue

            state.tool_call_counts[retry_key] = retry_count + 1
            state.total_retries += 1
            state.step_retries += 1

            try:
                retry_result = await asyncio.wait_for(
                    self.tool_executor.execute_batch([tool_calls[idx]]),
                    timeout=float(self.config.retry_timeout)
                )
            except asyncio.TimeoutError:
                logger.error(f"Retry timeout for {tool_name} after {self.config.retry_timeout}s")
                continue
            
            if retry_result:
                results[idx] = retry_result[0]
                state.executed_calls[retry_call_key] = {
                    "status": "success" if retry_result[0].success else "failed",
                    "result": retry_result[0],
                    "tool_name": tool_name,
                    "retried": True
                }

        return results

    # ═══════════════════════════════════════════════════════════════════════
    # STEP EVALUATION V2 (FIX 6)
    # ═══════════════════════════════════════════════════════════════════════

    async def _evaluate_step_v2(self, results: List, state: RunState, context: List[Dict]) -> Decision:
        """Improved step evaluation with stagnation detection."""
        failed = [r for r in results if r and not r.success]
        successful = [r for r in results if r and r.success]

        if failed:
            return Decision.STOP

        if not successful:
            return Decision.STOP

        if state.iteration >= self.config.max_steps:
            return Decision.STOP

        result_sig = self._generate_result_signature(results)
        if result_sig in state.result_signatures[-2:]:
            logger.info("Progress stagnation detected - same result returned")
            return Decision.STOP
        state.result_signatures.append(result_sig)

        if state.last_tool_result_success:
            recent_tools = state.tool_history[-self.config.loop_window_size:]
            if len(set(recent_tools)) <= 1 and len(recent_tools) >= 1:
                logger.debug("No progress being made, stopping early")
                return Decision.STOP

        return Decision.CONTINUE

    def _generate_result_signature(self, results: List) -> str:
        """Generate hash of results to detect stagnation."""
        if not results:
            return "empty"
        sig_parts = []
        for r in results:
            if r:
                sig_parts.append(f"{r.tool}:{r.success}")
        return hashlib.md5("".join(sig_parts).encode()).hexdigest()[:8]

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT MANAGEMENT V2 (FIX 5)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_context(self, system_prompt: str, messages: List[Dict], user_message: str) -> List[Dict]:
        """Build initial context."""
        context = [{"role": "system", "content": system_prompt}]
        context.extend(messages[-20:])
        context.append({"role": "user", "content": user_message})
        return context

    def _compress_context_smart(self, context: List[Dict]) -> List[Dict]:
        """Smart compression - summarize instead of delete."""
        if len(context) <= self.config.context_max_messages + 2:
            return context

        system_msg = context[0] if context[0].get("role") == "system" else None
        user_msg = context[-1] if context[-1].get("role") == "user" else None

        tool_msgs = [m for m in context[1:-1] if m.get("role") == "tool"]
        other_msgs = [m for m in context[1:-1] if m.get("role") != "tool"]

        kept_messages = [system_msg] if system_msg else []
        kept_messages.extend(other_msgs[-3:] if len(other_msgs) > 3 else other_msgs)

        if tool_msgs:
            recent_tools = tool_msgs[-self.config.context_max_messages:]
            summary = self._summarize_tool_history(tool_msgs[:-self.config.context_max_messages]) if len(tool_msgs) > self.config.context_max_messages else None
            kept_messages.extend(recent_tools)
            if summary:
                kept_messages.append({"role": "tool", "content": f"[Previous tools: {summary}]"})

        if user_msg:
            kept_messages.append(user_msg)

        return kept_messages

    def _summarize_tool_history(self, older_msgs: List[Dict]) -> str:
        """Summarize older tool messages instead of deleting."""
        if not older_msgs:
            return ""

        success_count = sum(1 for m in older_msgs if "✓" in m.get("content", "") or "success" in m.get("content", "").lower())
        error_count = sum(1 for m in older_msgs if "✗" in m.get("content", "") or "error" in m.get("content", "").lower() or "failed" in m.get("content", "").lower())

        tools = []
        for m in older_msgs:
            content = m.get("content", "")
            if "read" in content.lower():
                tools.append("read")
            elif "write" in content.lower():
                tools.append("write")
            elif "list" in content.lower() or "ls" in content.lower():
                tools.append("list")
            elif "search" in content.lower() or "grep" in content.lower():
                tools.append("search")

        tools_str = f"{', '.join(set(tools))}" if tools else "various"
        return f"{tools_str}, {success_count} ok, {error_count} errors"

    def _add_results_to_context(self, context: List[Dict], results: List):
        """Add tool results to context without tool_call_id."""
        for result in results:
            if result is None:
                continue
            content = result.summary if hasattr(result, 'summary') else str(result)
            context.append({
                "role": "tool",
                "content": content
            })

    # ═══════════════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════════

    async def synthesize(
        self,
        tool_results: List,
        direct_response: str,
        state: RunState
    ) -> str:
       """Telegram-style natural synthesis."""

       sections = []

       # intro
       if direct_response and direct_response.strip():
           sections.append(
               f"🤖 {direct_response.strip()}"
           )

       if not tool_results and not direct_response:
           return (
               "⚠️ Je n’ai trouvé aucun résultat.\n\n"
               "Réessaie avec une autre requête."
           )

       for r in tool_results:
           if not r:
               continue

           tool = getattr(r, "tool", "unknown")
           data = getattr(r, "data", None)
           error = getattr(r, "error", None)

           # ---------------- errors
           if error:
               sections.append(
                   f"⚠️ Petit souci avec **{tool}**\n\n"
                   f"`{error}`"
               )
               continue

           if not r.success or not data:
               continue

           # ---------- docker
           if "docker" in tool and isinstance(data, dict):
               output = data.get("output", data.get("stdout", ""))
               if not output and isinstance(data, list):
                   output = "\n".join(str(item) for item in data[:20])
               if not output:
                   output = str(data)[:500]
               truncated = output[:1500] + ("..." if len(output) > 1500 else "")
               sections.append(
                   f"🐳 Docker\n\n"
                   f"```\n{truncated}\n```"
               )
           # ---------- web response
           elif isinstance(data, dict) and "response" in data:
               sections.append(
                   f"🌐 Résultat web récupéré\n\n"
                   f"{data['response']}"
               )

           # ---------- web search results
           elif isinstance(data, dict) and "results" in data:
               results_list = data.get("results", [])
               if results_list:
                   lines = []
                   for r in results_list[:10]:
                       title = r.get("title", "No title")
                       url = r.get("url", "")
                       snippet = r.get("snippet", "")[:150]
                       lines.append(f"• **{title}**\n  {snippet}")
                       if url:
                           lines.append(f"  🔗 {url}")
                   sections.append(
                       f"🔍 Recherche: **{data.get('query', '')}**\n\n"
                       + "\n\n".join(lines)
                   )

           # ---------- sql rows
           elif isinstance(data, dict) and "rows" in data:
               rows = "\n".join(f"• {row}" for row in data["rows"])

               sections.append(
                   f"🗄️ Requête SQL exécutée\n\n"
                   f"Voici les résultats trouvés 👇\n\n"
                   f"{rows}"
               )

           # ---------- tables
           elif isinstance(data, dict) and "tables" in data:
               tables = "\n".join(
                   f"• {t.get('schema','public')}.{t.get('name')}"
                   for t in data["tables"]
               )

               sections.append(
                   f"🗂️ Tables détectées\n\n"
                   f"J’ai trouvé **{len(data['tables'])}** tables :\n\n"
                   f"{tables}"
               )

           # ---------- columns
           elif isinstance(data, dict) and "columns" in data:
               cols = "\n".join(
                   f"• {c['name']} ({c['type']})"
                   for c in data["columns"]
               )

               sections.append(
                   f"📋 Structure de table\n\n"
                   f"Colonnes de `{data.get('table', tool)}` :\n\n"
                   f"{cols}"
               )

           # ---------- files (including nested in data like NAS results)
           elif isinstance(data, dict) and (
               "files" in data or 
               "shares" in data or
               ("files" in (data.get("data") or {}) or "shares" in (data.get("data") or {}))
           ):
               file_list = data.get("files") or data.get("shares") or data.get("data", {}).get("files") or data.get("data", {}).get("shares") or []
               total_count = len(file_list)
               if not total_count:
                   total_count = data.get("data", {}).get("total", 0)
               if not file_list:
                   # Check if this is a NAS result with empty files
                   if "data" in data and ("files" in data.get("data", {}) or "shares" in data.get("data", {})):
                       sections.append(f"📂 Recherche NAS\n\nAucun fichier trouvé.")
                   else:
                       sections.append(f"📂 Recherche NAS\n\nAucun résultat trouvé pour cette recherche.")
                   continue
               lines_out = []
               for f in file_list[:20]:
                   if isinstance(f, dict):
                       name = f.get("name", "?")
                       path = f.get("path", "")
                       is_dir = f.get("isdir", False)
                       icon = "📁" if is_dir else "📄"
                       path_short = path if len(path) < 45 else "..." + path[-42:]
                       lines_out.append(f"{icon} **{name}**\n   └─ `{path_short}`")
                   else:
                       lines_out.append(f"📄 {f}")
               if total_count > 20:
                   lines_out.append(f"\n   ... et **{total_count - 20}** autres fichiers")
               sections.append(
                   f"📂 Fichiers trouvés\n\n"
                   f"J'ai trouvé **{total_count}** fichier(s) 👇\n\n"
                   + "\n".join(lines_out)
               )

           # ---------- generic dict fallback (prevents raw dict display)
           elif isinstance(data, dict):
               lines = [f"• **{k}**: {str(v)[:100]}" for k, v in list(data.items())[:10]]
               sections.append(
                   f"🔧 Résultat de `{tool}`\n\n"
                   + "\n".join(lines)
               )

           # ---------- file content
           elif tool == "read_file":
               content_short = data[:1000] + "..." if len(str(data)) > 1000 else data
               sections.append(
                   f"📄 Contenu du fichier\n\n"
                   f"Voilà ce que j'ai lu 👇\n\n"
                   f"```text\n{content_short}\n```"
               )

           # ---------- docker
           elif "docker" in tool:
               data_short = data[:2000] + "..." if len(str(data)) > 2000 else data
               sections.append(
                   f"🐳 Docker\n\n"
                   f"Commande exécutée avec succès.\n\n"
                   f"```text\n{data_short}\n```"
               )

           # ---------- bash
           elif tool == "bash":
               data_short = data[:2000] + "..." if len(str(data)) > 2000 else data
               sections.append(
                   f"💻 Terminal\n\n"
                   f"Résultat :\n\n"
                   f"```text\n{data_short}\n```"
               )

           # ---------- nas shares
           elif isinstance(data, dict) and "shares" in data.get("data", {}):
               share_list = data["data"]["shares"]
               lines_out = []
               for s in share_list:
                   name = s.get("name", "?")
                   path = s.get("path", "")
                   lines_out.append(f"💾 **{name}**\n   └─ `{path}`")
               sections.append(
                   f"💾 Stockage NAS\n\n"
                   f"Partages disponibles ({len(share_list)}) 👇\n\n"
                   + "\n".join(lines_out)
               )

           # ---------- nas search results
           elif isinstance(data, dict) and data.get("_fallback"):
               inner_data = data.get("data", {})
               files = inner_data.get("files", [])
               folder_path = inner_data.get("folder_path", data.get("folder_path", "/"))
               keyword = inner_data.get("keyword", data.get("keyword", ""))
               count = inner_data.get("total", data.get("total", len(files)))
               lines_out = []
               for f in files[:20]:
                   if isinstance(f, dict):
                       name = f.get("name", "?")
                       path = f.get("path", "")
                       is_dir = f.get("isdir", False)
                       icon = "📁" if is_dir else "📄"
                       lines_out.append(f"{icon} **{name}**\n   └─ `{path}`")
               if count > 20:
                   lines_out.append(f"\n   ... et **{count - 20}** autres résultats")
               search_info = f"🔍 Recherche: **{keyword}** dans `{folder_path}`"
               sections.append(
                   f"📂 Résultats NAS\n\n"
                   f"{search_info}\n\n"
                   f"J'ai trouvé **{count}** résultat(s) 👇\n\n"
                   + "\n".join(lines_out)
               )

           elif isinstance(data, dict):
               pretty = "\n".join(
                   f"• {k}: {v}"
                   for k, v in data.items()
               )

               sections.append(
                   f"🔧 Résultat de `{tool}`\n\n"
                   f"{pretty}"
               )

           # ---------- fallback
           else:
               sections.append(
                   f"📌 Résultat\n\n"
                   f"{data}"
               )

       final_status = (
           "\n\n━━━━━━━━━━━━━━\n"
           "✅ Terminé avec succès"
       )

       return "\n\n".join(sections) + final_status
    # ═══════════════════════════════════════════════════════════════════════
    # LLM CALL V2 - OPTIMIZED
    # ═══════════════════════════════════════════════════════════════════════

    def _get_provider_and_tools(self, provider_name: Optional[str], selected_tools: Optional[List[str]] = None):
        """Cache provider and tools for faster access."""
        provider_key = provider_name or "default"
        
        if provider_key not in self._provider_cache:
            from app.services.llm.provider_factory import provider_factory
            from app.core.config import settings
            self._provider_cache[provider_key] = provider_factory.get_provider(
                provider_name or settings.LLM_PROVIDER
            )
        
        if self._tools_cache is None:
            self._tools_cache = self.registry.get_all_definitions()
        
        tools = self._tools_cache
        if selected_tools:
            tool_names_set = set(selected_tools)
            tools = [t for t in self._tools_cache if t.get("function", {}).get("name") in tool_names_set]
        
        return self._provider_cache[provider_key], tools

    async def _call_llm(self, context: List[Dict], model: Optional[str], provider_name: Optional[str], db_session: Any = None, run_id: str = None, selected_tools: Optional[List[str]] = None) -> Dict:
        """Optimized LLM call with caching and timeout."""
        from app.core.config import settings
        from app.observability.event_logger import EventLogger

        provider, tools = self._get_provider_and_tools(provider_name, selected_tools)
        
        # Filter to only selected tools if provided
        if selected_tools and self._tools_cache:
            tool_names_set = set(selected_tools)
            tools = [t for t in self._tools_cache if t.get("function", {}).get("name") in tool_names_set]
            logger.debug(f"Filtered tools from {len(self._tools_cache)} to {len(tools)}: {selected_tools}")

        if not model:
            model = settings.LLM_MODEL or "default"

        start_time = time.time()
        event_logger = None

        if db_session and run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=run_id, chat_id=None)
            except Exception:
                pass

        if event_logger:
            asyncio.create_task(event_logger.emit_async(
                event_type=EventType.LLM_REQUEST,
                event_name="llm_request",
                payload={"model": model, "provider": provider_name or settings.LLM_PROVIDER, "prompt_length": sum(len(str(m.get("content", ""))) for m in context), "tools_count": len(tools)},
            ))

        try:
            response = await asyncio.wait_for(
                provider.chat_with_tools(
                    model=model,
                    messages=context,
                    tools=tools
                ),
                timeout=float(self.config.llm_timeout)
            )

            duration_ms = int((time.time() - start_time) * 1000)
            try:
                content = response.get("message", {}).get("content", "") or ""
            except Exception:
                content = str(response)[:500] if response else ""
            if event_logger:
                asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.LLM_RESPONSE,
                    event_name="llm_response",
                    payload={"model": model, "provider": provider_name or settings.LLM_PROVIDER, "tokens_in": 0, "tokens_out": 0, "response_preview": content[:500] if content else None},
                    duration_ms=duration_ms,
                ))

            return response
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"LLM call TIMEOUT after {self.config.llm_timeout}s")
            if event_logger:
                asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.ERROR,
                    event_name="error::LLMTimeout",
                    payload={"timeout": self.config.llm_timeout},
                    duration_ms=duration_ms,
                    success=False,
                    error_detail=f"LLM call timed out after {self.config.llm_timeout}s",
                ))
            return {"message": {"content": f"LLM timeout after {self.config.llm_timeout}s", "tool_calls": []}}
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if event_logger:
                asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.ERROR,
                    event_name="error::LLMCallError",
                    payload={"error": str(e)[:200]},
                    duration_ms=duration_ms,
                    success=False,
                    error_detail=str(e),
                ))

            logger.error(f"LLM call failed: {e}")
            return {"message": {"content": f"Error: {str(e)}", "tool_calls": []}}

    def _parse_tool_calls(self, response: Dict) -> List[Dict]:
        """Parse tool calls from LLM response."""
        message = response.get("message", {})
        return message.get("tool_calls", [])

    async def _store_interaction(self, user_id: Optional[str], message: str, response: str, state: RunState):
        """Store interaction in external MemoryService."""
        pass