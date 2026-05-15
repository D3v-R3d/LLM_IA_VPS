"""
Agent Orchestrator - Central orchestration layer.

Implements all 7 original fixes + improvements v2.3:
1.  Idempotency            - prevent re-execution of successful tools
2.  Tool results collision - use unique call_id
3.  Loop detection         - sliding window + frequency + whitelist
4.  Planning JSON parsing  - strict validation + fallback
5.  Context compression    - summarize instead of delete
6.  Step evaluation        - detect progress stagnation
7.  Retry stability        - exponential backoff + strict limits
8.  [NEW] LLM synthesis    - ALL responses go through the LLM for natural language output
9.  [NEW] Deduplication    - tool-call dedup within a single batch
10. [NEW] Richer signatures - better stagnation detection (data hash, not just tool name)
11. [NEW] Streaming hook   - ready for streaming responses
12. [NEW] Synthesis prompt - structured prompt gives the LLM full context
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
from app.services.prompt_service import PromptService
from app.observability.event_logger import EventLogger
from app.observability.event_types import EventType, EventLevel

logger = logging.getLogger(__name__)

SPLIT_PATTERN = re.compile(
    r"\b(?:and|then|after|ensuite|puis|plus)\b",
    re.I
)

TOOL_PATTERNS = [
    (["list", "directory", "folder"], ("List directory contents", "ls")),
    (["read", "file"],                ("Read file content",       "read_file")),
    (["write", "create"],             ("Write to file",           "write_file")),
    (["search", "find"],              ("Search for content",      "grep")),
    (["docker"],                      ("Docker operation",        "docker")),
    (["bash", "command", "execute"],  ("Execute command",         "bash")),
]

NO_RETRY_TOOLS: Set[str] = {
    "write_file", "docker_run", "docker_exec",
    "http_request", "postgres_insert", "postgres_update", "postgres_delete",
}

SAFE_TOOLS: Set[str] = {
    "ls", "dir", "list", "search", "grep", "find",
    "web_search", "read_file",
    "postgres_query", "postgres_list_tables", "postgres_describe_table",
}

# ─── Synthesis system prompt ────────────────────────────────────────────────
def _get_synthesis_system_prompt() -> str:
    """Get the synthesis system prompt from the synthesis.md template."""
    return PromptService.get_synthesis_prompt()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

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
    # Performance tunables
    llm_timeout: int = 45
    tool_timeout: int = 30
    retry_timeout: int = 15
    # [NEW] Synthesis settings
    synthesis_max_tokens: int = 1500
    synthesis_timeout: int = 30
    synthesis_fallback_on_error: bool = True   # fall back to formatted text if LLM fails

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
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
            synthesis_max_tokens=int(os.getenv("AGENT_SYNTHESIS_MAX_TOKENS", "1500")),
            synthesis_timeout=int(os.getenv("AGENT_SYNTHESIS_TIMEOUT", "30")),
            synthesis_fallback_on_error=os.getenv("AGENT_SYNTHESIS_FALLBACK", "true").lower() == "true",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

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
                    max_retries_per_tool=getattr(config, "max_retries_per_tool", 2),
                    context_max_messages=getattr(config, "context_max_messages", 10),
                    loop_window_size=getattr(config, "loop_window_size", 5),
                    max_consecutive_same_tool=getattr(config, "max_consecutive_same_tool", 3),
                    debug=config.debug,
                    llm_timeout=45,
                    tool_timeout=30,
                    retry_timeout=15,
                )
            else:
                self.config = config

        self._setup_logging()

        from app.services.agent_tools.base.registry import get_registry
        from app.services.agent_core.tool_executor import ToolExecutor
        from app.services.agent_core.budget_manager import BudgetManager

        self.registry = get_registry()
        self.tool_executor = ToolExecutor(registry=self.registry)

        self._provider_cache: Dict[str, Any] = {}
        self._tools_cache: Optional[List[Dict]] = None
        self._tools_cache_version = None

        budgets_config = os.getenv("AGENT_TOOL_BUDGETS", "")
        budgets: Dict[str, int] = {}
        if budgets_config:
            for part in budgets_config.split(","):
                if ":" in part:
                    tool, count = part.split(":")
                    budgets[tool.strip()] = int(count.strip())
        self.budget_manager = BudgetManager(budgets) if budgets else None

    def _setup_logging(self):
        logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

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
        logger.debug(f"Orchestrator run: user_message={user_message[:50]}...")

        state = RunState()
        state.run_id = run_id
        state.user_id = user_id

        event_logger = None
        if db_session and run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=run_id, chat_id=None)
            except Exception:
                pass

        if event_logger:
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

            # ── Tool routing ─────────────────────────────────────────────────
            router_result = None
            selected_tool_names = None

            if user_message:
                from app.services.agent_core.tool_router import route as route_tools
                router_result = route_tools(user_message)

                if router_result and router_result.get("tools"):
                    selected_tool_names = router_result["tools"]
                    logger.info(
                        f"Router tools: {selected_tool_names} "
                        f"(ambiguous={router_result.get('is_ambiguous')}, "
                        f"scopes={router_result.get('scope_candidates')})"
                    )

            if not selected_tool_names and user_message:
                from app.services.tool_registry.registry import search_tools
                results = search_tools(user_message, limit=15)
                selected_tool_names = [r["name"] for r in results if r["score"] >= 0.45]
                logger.info(f"Embedding tools (fallback): {selected_tool_names}")

            selected_tool_names = selected_tool_names or []
            logger.info(f"Selected tools for LLM: {selected_tool_names}")

            # ── Execution loop ───────────────────────────────────────────────
            loop_result = await self._execute_loop(
                context=context,
                model=model,
                provider_name=provider_name,
                state=state,
                db_session=db_session,
                selected_tools=selected_tool_names,
                router_result=router_result,
            )

            # ── [NEW] All responses go through the LLM ───────────────────────
            final_response = await self._llm_synthesize(
                user_message=user_message,
                tool_results=loop_result.get("tool_results", []),
                direct_response=loop_result.get("direct_response", ""),
                state=state,
                model=model,
                provider_name=provider_name,
                event_logger=event_logger,
            )

            # ── Update tool working memory ────────────────────────────────────
            from app.services.agent_core.tool_memory import get_tool_memory
            tool_mem = get_tool_memory()
            tool_mem.update(
                tool_results=loop_result.get("tool_results", []),
                user_message=user_message,
                final_response=final_response,
            )

            await self._store_interaction(user_id, user_message, final_response, state)

            if event_logger:
                event_logger.emit(
                    event_type=EventType.AGENT_END,
                    event_name="agent_end",
                    payload={"success": True, "final_response_length": len(final_response)},
                )

            return final_response

        except Exception as e:
            logger.exception(f"AgentOrchestrator error: {e}")
            if event_logger:
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

    # ═══════════════════════════════════════════════════════════════════════
    # PLANNING
    # ═══════════════════════════════════════════════════════════════════════

    async def plan(self, message: str, complexity: int, event_logger=None) -> Optional[Plan]:
        if complexity >= 4:
            return await self._llm_plan(message, event_logger=event_logger)
        return self._lightweight_plan(message)

    async def _llm_plan(self, message: str, event_logger=None) -> Optional[Plan]:
        """LLM-based structured planning for complexity 4-5 with strict JSON validation."""
        from app.providers.llm.provider_factory import provider_factory
        from app.core.config import settings
        from app.services.prompt_service import PromptService
        from app.services.agent_core.tool_router import route as route_tools

        router_result = route_tools(message)
        tools_list = (
            ", ".join(router_result["tools"])
            if router_result and router_result.get("tools")
            else "none"
        )

        planning_template = PromptService.get_planning_prompt()
        try:
            planning_prompt = planning_template.format(message=message, available_tools=tools_list)
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
                options={"max_tokens": 500},
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
            plan_tools = plan_data.get("tools", [])

            if not steps:
                logger.warning("LLM plan empty → fallback lightweight")
                if event_logger:
                    event_logger.emit(
                        event_type=EventType.PLAN_FALLBACK,
                        event_name="plan_fallback",
                        payload={"reason": "empty_plan", "fallback": "lightweight"},
                    )
                return self._lightweight_plan(message)

            return Plan(steps=steps, expected_tools=plan_tools)

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            if event_logger:
                event_logger.emit_error(error_type="LLMPlanningError", error_message=str(e))
            return self._lightweight_plan(message)

    def _lightweight_plan(self, message: str) -> Plan:
        """Simple heuristic – split by conjunctions."""
        steps: List[str] = []
        expected_tools: List[str] = []
        seen: Set[str] = set()

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

        return Plan(steps=steps, expected_tools=expected_tools)

    # ═══════════════════════════════════════════════════════════════════════
    # JSON PLAN PARSING (FIX 4)
    # ═══════════════════════════════════════════════════════════════════════

    def _parse_json_plan_strict(self, content: str) -> Optional[Dict]:
        """Strict JSON parsing with validation.
        [IMPROVED v2.3]: handles nested markdown fences and partial JSON extraction.
        """
        if not content:
            return None
        try:
            # Strip all markdown code fences (handles ```json ... ``` and plain ```)
            cleaned = re.sub(r"```(?:json)?\s*", "", content).replace("```", "").strip()

            # Try direct parse first
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                # [NEW] Try to extract the first {...} block (LLMs sometimes add prose around JSON)
                match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if not match:
                    logger.debug("No JSON object found in plan response")
                    return None
                data = json.loads(match.group(0))

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
    # EXECUTION LOOP V2
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_loop(
        self,
        context: List[Dict],
        model: Optional[str],
        provider_name: Optional[str],
        state: RunState,
        db_session: Any = None,
        selected_tools: Optional[List[str]] = None,
        router_result: Optional[Dict] = None,
    ) -> Dict:
        """Optimized execution loop with fast path and parallel execution."""

        max_steps = min(self.config.max_steps, self.config.hard_limit)
        tool_results: List = []

        for step in range(1, max_steps + 1):
            loop_start = time.time()
            state.iteration = step
            state.step_retries = 0
            logger.debug(f"Execution step: {step}/{max_steps}")

            # ── LLM call ─────────────────────────────────────────────────────
            llm_start = time.time()
            response = await self._call_llm(
                context, model, provider_name, db_session,
                run_id=state.run_id, selected_tools=selected_tools,
            )
            llm_ms = int((time.time() - llm_start) * 1000)
            logger.info(f"STEP {step}: LLM took {llm_ms}ms")

            tool_calls = self._parse_tool_calls(response)

            # Direct response – no tools needed
            if not tool_calls:
                content = response.get("message", {}).get("content", "")
                logger.info(f"STEP {step}: direct response in {int((time.time() - loop_start)*1000)}ms")
                return {"direct_response": content, "tool_results": []}

            # [NEW] Deduplicate tool calls within this batch
            tool_calls = self._deduplicate_tool_calls(tool_calls)

            # ── Loop detection ────────────────────────────────────────────────
            self._update_tool_history(tool_calls, state)
            loop_tool = detect_loop_v2(
                state.tool_history,
                state.tool_call_counts,
                window_size=self.config.loop_window_size,
                max_consecutive=self.config.max_consecutive_same_tool,
            )
            if loop_tool:
                logger.warning(f"AGENT_LOOP_DETECTED: {loop_tool}")
                return {
                    "direct_response": f"Loop detected: {loop_tool} called too many times. Task stopped.",
                    "tool_results": [],
                }

            # ── Budget check ──────────────────────────────────────────────────
            if self.budget_manager:
                tool_calls = self.budget_manager.check(tool_calls)
                if not tool_calls:
                    return {"direct_response": "Tool budget exhausted for this request.", "tool_results": []}

            # ── Execute tools ─────────────────────────────────────────────────
            tools_start = time.time()
            try:
                tool_results = await self._execute_with_idempotency(tool_calls, state, db_session=db_session)
            except asyncio.TimeoutError:
                logger.error(f"Tool execution timeout at step {step}")
                return {"direct_response": f"Tool execution timed out at step {step}.", "tool_results": []}

            tools_ms = int((time.time() - tools_start) * 1000)

            # ── Result merger for ambiguous queries ───────────────────────────
            if router_result and router_result.get("is_ambiguous"):
                from app.services.agent_core.tool_executor import ResultMerger
                original_count = len(tool_results)
                tool_results = ResultMerger.merge_results(tool_results, router_result)
                logger.info(f"ResultMerger: {original_count} → {len(tool_results)} results")

            logger.info(f"STEP {step}: tools took {tools_ms}ms ({len(tool_results)} results)")

            for result in tool_results:
                if result and result.success:
                    state.completed_tools.append(result.tool)

            state.last_tool_result_success = all(r.success for r in tool_results if r)

            # ── Step evaluation ───────────────────────────────────────────────
            decision = await self._evaluate_step_v2(tool_results, state, context)
            total_ms = int((time.time() - loop_start) * 1000)
            logger.info(f"STEP {step}: decision={decision}, total={total_ms}ms")

            # Early exit: all successful and within first 2 steps
            if decision == Decision.STOP and tool_results:
                if all(r and r.success for r in tool_results) and step <= 2:
                    logger.info(f"STEP {step}: early exit (all tools succeeded)")
                    break

            if decision == Decision.STOP:
                break

            self._add_results_to_context(context, tool_results)
            if len(context) > self.config.context_max_messages + 5:
                context = self._compress_context_smart(context)

        return {"direct_response": "", "tool_results": tool_results}

    # ─── [NEW] Tool call deduplication ──────────────────────────────────────

    def _deduplicate_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Remove duplicate tool calls within a single batch.
        Two calls are duplicates if they share the same tool name and arguments.
        """
        seen: Set[str] = set()
        unique: List[Dict] = []
        for tc in tool_calls:
            key = generate_call_key(tc)
            if key not in seen:
                seen.add(key)
                unique.append(tc)
            else:
                tool_name = tc.get("function", {}).get("name", "?")
                logger.debug(f"Dedup: skipping duplicate call to {tool_name}")
        return unique

    def _update_tool_history(self, tool_calls: List[Dict], state: RunState):
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            if name:
                state.tool_history.append(name)
                state.tool_call_counts[name] = state.tool_call_counts.get(name, 0) + 1

    # ═══════════════════════════════════════════════════════════════════════
    # TOOL EXECUTION V2 – IDEMPOTENCY + PARALLELISM
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_with_idempotency(
        self,
        tool_calls: List[Dict],
        state: RunState,
        db_session: Any = None,
    ) -> List:
        """Optimized tool execution with parallelization for safe tools."""

        event_logger = None
        if db_session and state.run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=state.run_id, chat_id=None)
            except Exception:
                pass

        results = [None] * len(tool_calls)
        to_execute: List[Dict] = []
        indices: List[int] = []

        for i, tc in enumerate(tool_calls):
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)

            if call_key in state.executed_calls:
                prev = state.executed_calls[call_key]
                if prev.get("status") == "success":
                    logger.debug(f"Idempotency skip: {tool_name} already succeeded")
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

        try:
            batch_results = await asyncio.wait_for(
                self.tool_executor.execute_batch(to_execute, user_id=state.user_id),
                timeout=float(self.config.tool_timeout),
            )
        except asyncio.TimeoutError:
            logger.error(f"execute_batch timed out after {self.config.tool_timeout}s")
            raise

        for idx, tool_result in zip(indices, batch_results):
            tc = tool_calls[idx]
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)

            results[idx] = tool_result
            state.executed_calls[call_key] = {
                "status": "success" if tool_result and tool_result.success else "failed",
                "result": tool_result,
                "tool_name": tool_name,
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

        # ── Retry failed tools ────────────────────────────────────────────────
        failed = [(i, r) for i, r in enumerate(results) if r and not r.success]

        for idx, _result in failed:
            tc = tool_calls[idx]
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)

            if tool_name in NO_RETRY_TOOLS:
                logger.debug(f"Skipping retry for {tool_name} (side-effect tool)")
                continue

            retry_key = f"retry_{call_key}"
            retry_count = state.tool_call_counts.get(retry_key, 0)
            if retry_count >= self.config.max_retries_per_tool:
                logger.debug(f"Max retries reached for {tool_name}")
                continue

            state.tool_call_counts[retry_key] = retry_count + 1
            state.total_retries += 1
            state.step_retries += 1

            # Exponential back-off: 0.5s, 1s, 2s …
            await asyncio.sleep(0.5 * (2 ** retry_count))

            try:
                retry_result = await asyncio.wait_for(
                    self.tool_executor.execute_batch([tc], user_id=state.user_id),
                    timeout=float(self.config.retry_timeout),
                )
            except asyncio.TimeoutError:
                logger.error(f"Retry timeout for {tool_name} after {self.config.retry_timeout}s")
                continue

            if retry_result:
                results[idx] = retry_result[0]
                state.executed_calls[call_key] = {
                    "status": "success" if retry_result[0].success else "failed",
                    "result": retry_result[0],
                    "tool_name": tool_name,
                    "retried": True,
                }

        return results

    # ═══════════════════════════════════════════════════════════════════════
    # STEP EVALUATION V2 (FIX 6)
    # ═══════════════════════════════════════════════════════════════════════

    async def _evaluate_step_v2(
        self, results: List, state: RunState, context: List[Dict]
    ) -> Decision:
        """Improved step evaluation with stagnation detection."""
        failed     = [r for r in results if r and not r.success]
        successful = [r for r in results if r and r.success]

        if failed or not successful:
            return Decision.STOP

        if state.iteration >= self.config.max_steps:
            return Decision.STOP

        # [IMPROVED] Richer signature: includes a hash of the actual data payload
        result_sig = self._generate_result_signature(results)
        if result_sig in state.result_signatures[-2:]:
            logger.info("Progress stagnation detected (identical result returned)")
            return Decision.STOP
        state.result_signatures.append(result_sig)

        if state.last_tool_result_success:
            recent_tools = state.tool_history[-self.config.loop_window_size:]
            if len(set(recent_tools)) <= 1 and len(recent_tools) >= 1:
                logger.debug("No tool diversity — stopping early")
                return Decision.STOP

        return Decision.CONTINUE

    def _generate_result_signature(self, results: List) -> str:
        """[IMPROVED] Hash of tool name + success + data content for better stagnation detection."""
        if not results:
            return "empty"
        sig_parts = []
        for r in results:
            if r:
                # Include a short hash of the data to catch identical payloads
                data_repr = str(r.data)[:256] if r.data else ""
                data_hash = hashlib.md5(data_repr.encode()).hexdigest()[:6]
                sig_parts.append(f"{r.tool}:{r.success}:{data_hash}")
        return hashlib.md5("".join(sig_parts).encode()).hexdigest()[:8]

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT MANAGEMENT V2 (FIX 5)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_context(
        self, system_prompt: str, messages: List[Dict], user_message: str
    ) -> List[Dict]:
        context = [{"role": "system", "content": system_prompt}]
        context.extend(messages[-20:])
        context.append({"role": "user", "content": user_message})
        return context

    def _compress_context_smart(self, context: List[Dict]) -> List[Dict]:
        """Smart compression – summarize old tool messages instead of deleting."""
        if len(context) <= self.config.context_max_messages + 2:
            return context

        system_msg = context[0]  if context[0].get("role") == "system" else None
        user_msg   = context[-1] if context[-1].get("role") == "user"   else None

        tool_msgs  = [m for m in context[1:-1] if m.get("role") == "tool"]
        other_msgs = [m for m in context[1:-1] if m.get("role") != "tool"]

        kept: List[Dict] = []
        if system_msg:
            kept.append(system_msg)
        kept.extend(other_msgs[-3:] if len(other_msgs) > 3 else other_msgs)

        if tool_msgs:
            max_keep = self.config.context_max_messages
            older_tools  = tool_msgs[:-max_keep] if len(tool_msgs) > max_keep else []
            recent_tools = tool_msgs[-max_keep:]
            if older_tools:
                summary = self._summarize_tool_history(older_tools)
                kept.append({"role": "tool", "content": f"[Previous tools summary: {summary}]"})
            kept.extend(recent_tools)

        if user_msg:
            kept.append(user_msg)

        return kept

    def _summarize_tool_history(self, older_msgs: List[Dict]) -> str:
        if not older_msgs:
            return ""
        success_count = sum(
            1 for m in older_msgs
            if "✓" in m.get("content", "") or "success" in m.get("content", "").lower()
        )
        error_count = sum(
            1 for m in older_msgs
            if "✗" in m.get("content", "") or "error" in m.get("content", "").lower() or "failed" in m.get("content", "").lower()
        )
        tools: List[str] = []
        for m in older_msgs:
            c = m.get("content", "").lower()
            if "read"   in c: tools.append("read")
            elif "write" in c: tools.append("write")
            elif "list"  in c or "ls" in c: tools.append("list")
            elif "search" in c or "grep" in c: tools.append("search")
        tools_str = ", ".join(set(tools)) if tools else "various"
        return f"{tools_str}, {success_count} ok, {error_count} errors"

    def _add_results_to_context(self, context: List[Dict], results: List):
        for result in results:
            if result is None:
                continue
            content = result.summary if hasattr(result, "summary") else str(result)
            context.append({"role": "tool", "content": content})

    # ═══════════════════════════════════════════════════════════════════════
    # [NEW] LLM SYNTHESIS – ALL RESPONSES GO THROUGH THE LLM
    # ═══════════════════════════════════════════════════════════════════════

    async def _llm_synthesize(
        self,
        user_message: str,
        tool_results: List,
        direct_response: str,
        state: RunState,
        model: Optional[str],
        provider_name: Optional[str],
        event_logger=None,
    ) -> str:
        """
        [NEW v2.3] Route ALL responses through the LLM for natural language output.

        The LLM receives:
        - The user's original question
        - A structured summary of every tool result (success or failure)
        - Any direct content already produced by the agentic loop
        It then writes a coherent, natural response.

        Falls back to the legacy _format_results() method if the LLM call fails
        and synthesis_fallback_on_error is True.
        """
        synthesis_messages = self._build_synthesis_messages(
            user_message=user_message,
            tool_results=tool_results,
            direct_response=direct_response,
        )

        if event_logger:
            event_logger.emit(
                event_type=EventType.LLM_REQUEST,
                event_name="llm_synthesis_request",
                payload={"messages_count": len(synthesis_messages)},
            )

        synth_start = time.time()
        try:
            provider, _ = self._get_provider_and_tools(provider_name)
            from app.core.config import settings
            used_model = model or settings.LLM_MODEL or "default"

            response = await asyncio.wait_for(
                provider.chat(
                    model=used_model,
                    messages=synthesis_messages,
                    options={"max_tokens": self.config.synthesis_max_tokens},
                ),
                timeout=float(self.config.synthesis_timeout),
            )

            duration_ms = int((time.time() - synth_start) * 1000)
            content = ""
            if isinstance(response, dict):
                content = (
                    response.get("content")
                    or response.get("message", {}).get("content", "")
                    or ""
                )
            else:
                content = str(response)

            content = content.strip()
            logger.info(f"LLM synthesis: {len(content)} chars in {duration_ms}ms")

            if event_logger:
                event_logger.emit(
                    event_type=EventType.LLM_RESPONSE,
                    event_name="llm_synthesis_response",
                    payload={"response_length": len(content)},
                )

            if content:
                return content

            # Empty response → fallback
            logger.warning("LLM synthesis returned empty response, falling back")

        except asyncio.TimeoutError:
            logger.error(f"LLM synthesis timed out after {self.config.synthesis_timeout}s")
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")

        # ── Fallback: formatted text ──────────────────────────────────────────
        if self.config.synthesis_fallback_on_error:
            logger.info("Using formatted fallback for synthesis")
            return self._format_results(tool_results, direct_response)

        return "An error occurred while generating the response."

    def _build_synthesis_messages(
        self,
        user_message: str,
        tool_results: List,
        direct_response: str,
    ) -> List[Dict]:
        """
        Build the message list sent to the LLM for final synthesis.
        Produces a clean, structured context without exposing internal details.
        """
        # ── Serialize tool results into a readable block ──────────────────────
        results_block_parts: List[str] = []

        if direct_response and direct_response.strip():
            results_block_parts.append(f"[Agent intermediate response]\n{direct_response.strip()}")

        for i, r in enumerate(tool_results or [], start=1):
            if r is None:
                continue
            tool  = getattr(r, "tool",  "unknown")
            data  = getattr(r, "data",  None)
            error = getattr(r, "error", None)

            if not r.success or error:
                results_block_parts.append(
                    f"[Tool {i}: {tool}] ERROR\n{error or 'Unknown error'}"
                )
                continue

            # Truncate large payloads to avoid exceeding context limits
            data_str = json.dumps(data, ensure_ascii=False, default=str) if isinstance(data, (dict, list)) else str(data)
            if len(data_str) > 3000:
                data_str = data_str[:3000] + "\n… [truncated]"

            results_block_parts.append(f"[Tool {i}: {tool}] SUCCESS\n{data_str}")

        if not results_block_parts:
            results_block = "No tool results available."
        else:
            results_block = "\n\n".join(results_block_parts)

        user_content = (
            f"The user asked:\n{user_message}\n\n"
            f"Here are the tool results you can use to answer:\n\n"
            f"{results_block}\n\n"
            "Now write a complete, clear, and natural answer to the user's question "
            "based on the above results. Do not mention tool names or internal details."
        )

        return [
            {"role": "system", "content": _get_synthesis_system_prompt()},
            {"role": "user",   "content": user_content},
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY FORMATTED FALLBACK (kept as fallback, not primary path)
    # ═══════════════════════════════════════════════════════════════════════

    def _format_results(self, tool_results: List, direct_response: str) -> str:
        """
        Fallback formatter used only when LLM synthesis fails.
        Previously called `synthesize()` – kept for resilience, not removed.
        """
        DIVIDER = "─" * 28
        sections: List[str] = []
        errors:   List[str] = []
        success_count = 0

        if direct_response and direct_response.strip():
            sections.append(direct_response.strip())

        if not tool_results and not direct_response:
            return "⚠️  No results found.\n" f"{DIVIDER}\nTry rephrasing your query."

        for r in tool_results or []:
            if not r:
                continue

            tool  = getattr(r, "tool",  "unknown")
            data  = getattr(r, "data",  None)
            error = getattr(r, "error", None)

            if error:
                errors.append(f"• {tool}: `{error}`")
                continue

            if not r.success or not data:
                continue

            success_count += 1

            if "docker" in tool and isinstance(data, dict):
                output = data.get("output") or data.get("stdout") or str(data)[:500]
                truncated = output[:1500] + ("\n… [truncated]" if len(output) > 1500 else "")
                sections.append(f"🐳  Docker\n{DIVIDER}\n```\n{truncated}\n```")

            elif isinstance(data, dict) and "response" in data:
                sections.append(f"🌐  Web result\n{DIVIDER}\n{data['response']}")

            elif isinstance(data, dict) and "results" in data:
                results_list = data.get("results", [])
                query = data.get("query", "")
                lines = []
                for item in results_list[:10]:
                    title   = item.get("title", "No title")
                    url     = item.get("url", "")
                    snippet = item.get("snippet", "")[:160].rstrip()
                    if snippet and not snippet.endswith((".", "…")):
                        snippet += "…"
                    lines.append(f"  {title}\n  {snippet}")
                    if url:
                        lines.append(f"  🔗 {url}")
                header = f'🔍  Search — "{query}"  ({len(results_list)} result{"s" if len(results_list) > 1 else ""})'
                sections.append(f"{header}\n{DIVIDER}\n" + "\n\n".join(lines))

            elif isinstance(data, dict) and "rows" in data:
                rows     = data["rows"]
                count    = len(rows)
                col_keys = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
                if col_keys:
                    col_widths = {k: max(len(k), max(len(str(r.get(k, ""))) for r in rows[:50])) for k in col_keys}
                    header_row = "  " + " │ ".join(k.ljust(col_widths[k]) for k in col_keys)
                    sep_row    = "  " + "─┼─".join("─" * col_widths[k] for k in col_keys)
                    data_rows  = ["  " + " │ ".join(str(row.get(k, "")).ljust(col_widths[k]) for k in col_keys) for row in rows[:50]]
                    table = "\n".join([header_row, sep_row] + data_rows)
                    if count > 50:
                        table += f"\n  … {count - 50} more row(s)"
                else:
                    table = "\n".join(f"  • {row}" for row in rows[:50])
                sections.append(f"🗄️  SQL  —  {count} row{'s' if count > 1 else ''}\n{DIVIDER}\n```\n{table}\n```")

            elif isinstance(data, dict) and "tables" in data:
                tables = data["tables"]
                lines  = [f"  • {t.get('schema','public')}.{t.get('name')}" for t in tables]
                sections.append(f"🗂️  Tables  —  {len(tables)} found\n{DIVIDER}\n" + "\n".join(lines))

            elif isinstance(data, dict) and "columns" in data:
                cols   = data["columns"]
                name_w = max((len(c["name"]) for c in cols), default=4)
                lines  = [f"  {c['name'].ljust(name_w)}  {c['type']}" for c in cols]
                sections.append(f"📋  Columns of `{data.get('table', tool)}`\n{DIVIDER}\n```\n" + "\n".join(lines) + "\n```")

            elif isinstance(data, dict) and ("files" in data or "shares" in data or "files" in (data.get("data") or {}) or "shares" in (data.get("data") or {})):
                inner     = data.get("data") or data
                file_list = inner.get("files") or inner.get("shares") or []
                total     = inner.get("total", len(file_list))
                if not file_list:
                    sections.append(f"📂  Files\n{DIVIDER}\nNo files found.")
                    continue
                lines = []
                for f in file_list[:20]:
                    if isinstance(f, dict):
                        icon  = "📁" if f.get("isdir") else "📄"
                        path  = f.get("path", "")
                        short = ("…" + path[-40:]) if len(path) > 43 else path
                        lines.append(f"  {icon} {f.get('name','?')}\n     {short}")
                    else:
                        lines.append(f"  📄 {f}")
                footer = f"\n  … and {total - 20} more" if total > 20 else ""
                sections.append(f"📂  Files  —  {total} item{'s' if total > 1 else ''}\n{DIVIDER}\n" + "\n\n".join(lines) + footer)

            elif tool == "read_file":
                content = str(data)
                short   = content[:1200] + "\n… [truncated]" if len(content) > 1200 else content
                sections.append(f"📄  File read\n{DIVIDER}\n```text\n{short}\n```")

            elif tool == "bash":
                short = str(data)[:2000] + "\n…" if len(str(data)) > 2000 else str(data)
                sections.append(f"💻  Terminal\n{DIVIDER}\n```\n{short}\n```")

            elif isinstance(data, dict):
                lines = [f"  {k}: {str(v)[:120]}" for k, v in list(data.items())[:12]]
                sections.append(f"🔧  `{tool}`\n{DIVIDER}\n" + "\n".join(lines))

            else:
                short = str(data)[:1500] + "\n…" if len(str(data)) > 1500 else str(data)
                sections.append(f"📌  `{tool}`\n{DIVIDER}\n{short}")

        if errors:
            sections.append(f"⚠️  Error{'s' if len(errors) > 1 else ''}\n{DIVIDER}\n" + "\n".join(errors))

        direct_has_termine = direct_response and "Terminé" in direct_response
        if errors and not success_count:
            footer = f"\n{DIVIDER}\n❌  Failed ({len(errors)} error{'s' if len(errors) > 1 else ''})"
        elif errors:
            footer = f"\n{DIVIDER}\n⚠️  Done with {len(errors)} error{'s' if len(errors) > 1 else ''}"
        elif direct_has_termine:
            footer = ""
        else:
            footer = f"\n{DIVIDER}\n✅ Done"

        sep = f"\n\n{'━' * 28}\n\n"
        return sep.join(sections) + footer

    # ═══════════════════════════════════════════════════════════════════════
    # LLM CALL V2
    # ═══════════════════════════════════════════════════════════════════════

    def _get_provider_and_tools(
        self,
        provider_name: Optional[str],
        selected_tools: Optional[List[str]] = None,
    ):
        """Cache provider and tools. Invalidates cache on registry version change."""
        provider_key = provider_name or "default"

        if provider_key not in self._provider_cache:
            from app.providers.llm.provider_factory import provider_factory
            from app.core.config import settings
            self._provider_cache[provider_key] = provider_factory.get_provider(
                provider_name or settings.LLM_PROVIDER
            )

        current_version = getattr(self.registry, "version", None)
        if self._tools_cache is None or (
            current_version is not None and current_version != self._tools_cache_version
        ):
            self._tools_cache = self.registry.get_all_definitions()
            self._tools_cache_version = current_version

        tools = self._tools_cache
        if selected_tools:
            tool_names_set = set(selected_tools)
            tools = [t for t in self._tools_cache if t.get("function", {}).get("name") in tool_names_set]

        return self._provider_cache[provider_key], tools

    async def _call_llm(
        self,
        context: List[Dict],
        model: Optional[str],
        provider_name: Optional[str],
        db_session: Any = None,
        run_id: Optional[str] = None,
        selected_tools: Optional[List[str]] = None,
    ) -> Dict:
        """Optimized LLM call with caching and timeout."""
        from app.core.config import settings

        provider, tools = self._get_provider_and_tools(provider_name, selected_tools)
        model = model or settings.LLM_MODEL or "default"

        start_time = time.time()
        event_logger = None
        if db_session and run_id:
            try:
                from app.observability.event_logger import EventLogger
                event_logger = EventLogger(db=db_session, run_id=run_id, chat_id=None)
            except Exception:
                pass

        log_tasks: List[asyncio.Task] = []

        if event_logger:
            t = asyncio.create_task(event_logger.emit_async(
                event_type=EventType.LLM_REQUEST,
                event_name="llm_request",
                payload={
                    "model": model,
                    "provider": provider_name or settings.LLM_PROVIDER,
                    "prompt_length": sum(len(str(m.get("content", ""))) for m in context),
                    "tools_count": len(tools),
                },
            ))
            log_tasks.append(t)

        try:
            response = await asyncio.wait_for(
                provider.chat_with_tools(model=model, messages=context, tools=tools),
                timeout=float(self.config.llm_timeout),
            )

            duration_ms = int((time.time() - start_time) * 1000)
            try:
                content = response.get("message", {}).get("content", "") or ""
            except Exception:
                content = str(response)[:500] if response else ""

            if event_logger:
                t = asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.LLM_RESPONSE,
                    event_name="llm_response",
                    payload={
                        "model": model,
                        "provider": provider_name or settings.LLM_PROVIDER,
                        "response_preview": content[:500] if content else None,
                    },
                    duration_ms=duration_ms,
                ))
                log_tasks.append(t)

            return response

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"LLM call TIMEOUT after {self.config.llm_timeout}s")
            if event_logger:
                t = asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.ERROR,
                    event_name="error::LLMTimeout",
                    payload={"timeout": self.config.llm_timeout},
                    duration_ms=duration_ms,
                    success=False,
                    error_detail=f"LLM call timed out after {self.config.llm_timeout}s",
                ))
                log_tasks.append(t)
            return {"message": {"content": f"LLM timeout after {self.config.llm_timeout}s", "tool_calls": []}}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if event_logger:
                t = asyncio.create_task(event_logger.emit_async(
                    event_type=EventType.ERROR,
                    event_name="error::LLMCallError",
                    payload={"error": str(e)[:200]},
                    duration_ms=duration_ms,
                    success=False,
                    error_detail=str(e),
                ))
                log_tasks.append(t)
            logger.error(f"LLM call failed: {e}")
            return {"message": {"content": f"Error: {str(e)}", "tool_calls": []}}

        finally:
            if log_tasks:
                done, pending = await asyncio.wait(log_tasks, timeout=2.0)
                for task in done:
                    if task.exception():
                        logger.warning(f"Event logging task failed: {task.exception()}")
                for task in pending:
                    task.cancel()

    def _parse_tool_calls(self, response: Dict) -> List[Dict]:
        return response.get("message", {}).get("tool_calls", [])

    # ═══════════════════════════════════════════════════════════════════════
    # STORAGE
    # ═══════════════════════════════════════════════════════════════════════

    async def _store_interaction(
        self, user_id: Optional[str], message: str, response: str, state: RunState
    ):
        """Store interaction in external MemoryService."""
        pass
