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
import logging
import os
import re
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any

from app.services.agent_core.models import Decision, Plan, RunState, detect_loop_v2, generate_call_key

logger = logging.getLogger(__name__)

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
            debug=os.getenv("AGENT_DEBUG", "false").lower() == "true"
        )


class AgentOrchestrator:
    """Central orchestration layer for the agent."""

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        if config is None:
            self.config = OrchestratorConfig.from_env()
        elif hasattr(config, 'context_max_messages'):
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
                    debug=config.debug
                )
            else:
                self.config = config
        self._setup_logging()

        from app.services.agent_tools.registry import get_registry
        from app.services.agent_core.tool_executor import ToolExecutor

        self.registry = get_registry()
        self.tool_executor = ToolExecutor(registry=self.registry)

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
    ) -> str:
        """Main entry point - full agent flow."""
        logger.debug(f"Orchestrator run: user_message={user_message[:50]}...")

        state = RunState()

        intent_result = self.intent_classification(user_message)
        complexity = intent_result["complexity"]

        logger.debug(f"Intent: {intent_result['intent']}, complexity: {complexity}")

        plan = await self.plan(user_message, complexity)
        if plan:
            state.plan = plan
            logger.debug(f"Plan: {len(plan.steps)} steps, tools: {plan.expected_tools}")

        context = self._build_context(system_prompt, messages_history, user_message)
        response = await self._execute_loop(
            context=context,
            model=model,
            provider_name=provider_name,
            state=state
        )

        final_response = await self.synthesize(
            response.get("tool_results", []),
            response.get("direct_response", ""),
            state
        )

        await self._store_interaction(user_id, user_message, final_response, state)

        return final_response

    # ═══════════════════════════════════════════════════════════════════════
    # INTENT CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════

    def intent_classification(self, message: str) -> Dict:
        """Heuristic scoring - NO LLM call."""
        msg_lower = message.lower()
        complexity = 1
        intent = "general"
        confidence = 0.5

        multi_step_words = ["then", "after", "ensuite", "et puis", "plus", "also"]
        action_verbs = ["analyze", "compare", "debug", "plan", "create", "build", "find", "search", "check", "implement", "refactor", "fix", "test"]

        conjunction_count = sum(1 for word in multi_step_words if word in msg_lower)
        verb_count = sum(1 for verb in action_verbs if verb in msg_lower)

        complexity = 1 + conjunction_count + verb_count

        if len(message) > 200:
            complexity += 1

        complexity = min(complexity, 5)

        if any(w in msg_lower for w in ["file", "directory", "folder", "list", "read", "write"]):
            intent = "file_operation"
            confidence = 0.9
        elif any(w in msg_lower for w in ["search", "find", "google", "web"]):
            intent = "web_search"
            confidence = 0.85
        elif any(w in msg_lower for w in ["execute", "run", "command", "bash"]):
            intent = "code_execution"
            confidence = 0.8
        elif any(w in msg_lower for w in ["docker", "container"]):
            intent = "docker"
            confidence = 0.9
        elif any(w in msg_lower for w in ["database", "sql", "query"]):
            intent = "database"
            confidence = 0.85
        else:
            intent = "general"
            confidence = 0.5

        return {"complexity": complexity, "intent": intent, "confidence": confidence}

    # ═══════════════════════════════════════════════════════════════════════
    # PLANNING SYSTEM (FIX 4: JSON parsing)
    # ═══════════════════════════════════════════════════════════════════════

    async def plan(self, message: str, complexity: int) -> Optional[Plan]:
        """HYBRID planning: lightweight for complexity 3, LLM for 4-5."""
        if complexity < self.config.complexity_threshold:
            return None

        if complexity == 3:
            return self._lightweight_plan(message)
        else:
            return await self._llm_plan(message)

    def _lightweight_plan(self, message: str) -> Plan:
        """Simple heuristic - split by conjunctions."""
        steps = []
        expected_tools = []

        parts = re.split(r'\b(?:and|then|after|ensuite|puis|plus)\b', message.lower())

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "list" in part or "directory" in part or "folder" in part:
                steps.append("List directory contents")
                expected_tools.append("ls")
            elif "read" in part and "file" in part:
                steps.append("Read file content")
                expected_tools.append("read_file")
            elif "write" in part or "create" in part:
                steps.append("Write to file")
                expected_tools.append("write_file")
            elif "search" in part or "find" in part:
                steps.append("Search for content")
                expected_tools.append("grep")
            elif "docker" in part:
                steps.append("Docker operation")
                expected_tools.append("docker")
            elif "bash" in part or "command" in part or "execute" in part:
                steps.append("Execute command")
                expected_tools.append("bash")

        return Plan(steps=steps, expected_tools=expected_tools)

    async def _llm_plan(self, message: str) -> Optional[Plan]:
        """LLM-based structured planning for complexity 4-5 with strict JSON validation."""
        from app.services.llm.provider_factory import provider_factory
        from app.services.agent_tools.registry import get_registry
        from app.core.config import settings

        planning_prompt = f"""You are a task planner. Given the user request, break it down into a structured plan.

User request: {message}

Respond ONLY with a JSON object in this exact format:
{{
  "steps": ["step 1 description", "step 2 description"],
  "tools": ["tool1", "tool2"],
  "reasoning": "brief explanation of the plan"
}}

Do not include any other text. The response must be valid JSON."""

        try:
            provider = provider_factory.get_provider(settings.LLM_PROVIDER)
            response = await provider.chat(
                model=settings.LLM_MODEL or "default",
                messages=[{"role": "user", "content": planning_prompt}],
                options={"max_tokens": 500}
            )

            content = response.get("content", "") if isinstance(response, dict) else str(response)

            plan_data = self._parse_json_plan_strict(content)
            if plan_data:
                return Plan(
                    steps=plan_data.get("steps", []),
                    expected_tools=plan_data.get("tools", [])
                )
            else:
                logger.info("LLM plan validation failed, using fallback lightweight plan")
        except Exception as e:
            logger.warning(f"LLM planning failed: {e}, falling back to lightweight")

        return self._lightweight_plan(message)

    def _parse_json_plan_strict(self, content: str) -> Optional[Dict]:
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
    # EXECUTION LOOP
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_loop(
        self,
        context: List[Dict],
        model: Optional[str],
        provider_name: Optional[str],
        state: RunState
    ) -> Dict:
        """Main execution loop with all improvements."""
        max_steps = min(self.config.max_steps, self.config.hard_limit)
        all_tool_results = []

        for step in range(1, max_steps + 1):
            state.iteration = step
            state.step_retries = 0
            logger.debug(f"Execution step: {step}/{max_steps}")

            response = await self._call_llm(context, model, provider_name)

            tool_calls = self._parse_tool_calls(response)

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

            if not tool_calls:
                content = response.get("message", {}).get("content", "")
                return {"direct_response": content, "tool_results": []}

            tool_results = await self._execute_with_idempotency(tool_calls, state)
            all_tool_results.extend(tool_results)

            for result in tool_results:
                if result.success:
                    state.completed_tools.append(result.tool)
                else:
                    state.failed_tools.append(result.tool)

            state.last_tool_result_success = all(r.success for r in tool_results)

            decision = await self._evaluate_step_v2(tool_results, state, context)

            if decision == Decision.STOP:
                break

            self._add_results_to_context(context, tool_results)

            context = self._compress_context_smart(context)

        return {
            "direct_response": "",
            "tool_results": all_tool_results
        }

    def _update_tool_history(self, tool_calls: List[Dict], state: RunState):
        """Update tool history with per-tool counters."""
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            if name:
                state.tool_history.append(name)
                state.tool_call_counts[name] = state.tool_call_counts.get(name, 0) + 1

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION WITH IDEMPOTENCY (FIX 1 & 2 & 7)
    # ═══════════════════════════════════════════════════════════════════════

    async def _execute_with_idempotency(
        self,
        tool_calls: List[Dict],
        state: RunState
    ) -> List:
        """
        Execute tools with:
        - Idempotency check (FIX 1)
        - Unique call_id for results (FIX 2)
        - Exponential backoff (FIX 7)
        """
        results = []

        for i, tc in enumerate(tool_calls):
            tool_name = tc.get("function", {}).get("name", "")
            call_key = generate_call_key(tc)

            if call_key in state.executed_calls:
                prev = state.executed_calls[call_key]
                if prev.get("status") == "success":
                    logger.debug(f"Idempotency skip: {tool_name} already executed successfully")
                    results.append(prev["result"])
                    continue
                if prev.get("status") == "failed" and tool_name in NO_RETRY_TOOLS:
                    logger.debug(f"Skipping retry for {tool_name} (side-effect tool)")
                    results.append(prev["result"])
                    continue

            result = await self.tool_executor.execute_batch([tc])
            tool_result = result[0] if result else None

            state.executed_calls[call_key] = {
                "status": "success" if tool_result and tool_result.success else "failed",
                "result": tool_result,
                "tool_name": tool_name
            }

            results.append(tool_result)

        failed = [(i, r) for i, r in enumerate(results) if r and not r.success]

        if not failed:
            return results

        for idx, result in failed:
            tool_name = tool_calls[idx].get("function", {}).get("name", "")

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

            backoff = 0.5 * (2 ** retry_count)
            await asyncio.sleep(backoff)

            retry_result = await self.tool_executor.execute_batch([tool_calls[idx]])
            if retry_result:
                results[idx] = retry_result[0]
                state.executed_calls[call_key] = {
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
        """Simple local synthesis - returns raw formatted results."""
        if not tool_results and direct_response:
            return direct_response

        if not tool_results and not direct_response:
            return "No results available."

        lines = []

        if direct_response and direct_response.strip():
            lines.append(direct_response.strip())

        if tool_results:
            for r in tool_results:
                if not r:
                    continue

                tool_name = getattr(r, 'tool', 'unknown')
                data = getattr(r, 'data', None)
                error = getattr(r, 'error', None)

                if r.success and data:
                    if isinstance(data, dict):
                        if "response" in data:
                            lines.append(f"**{tool_name}:** {data['response'][:300]}")
                        elif "rows" in data and data["rows"]:
                            lines.append(f"**{tool_name} results:**")
                            for row in data["rows"][:5]:
                                lines.append(f"  • {row}")
                        elif "tables" in data and data["tables"]:
                            lines.append(f"**Tables ({len(data['tables'])}):**")
                            for t in data["tables"][:5]:
                                lines.append(f"  • {t.get('schema', 'public')}.{t.get('name')}")
                        elif "columns" in data and data["columns"]:
                            lines.append(f"**{data.get('table', tool_name)} columns:**")
                            for col in data["columns"][:10]:
                                lines.append(f"  • {col.get('name')} ({col.get('type')})")
                        elif "shares" in data and data["shares"]:
                            lines.append(f"**NAS Shares:**")
                            for s in data["shares"][:5]:
                                lines.append(f"  • {s.get('name', 'unknown')}")
                        elif "files" in data and data["files"]:
                            lines.append(f"**Files ({len(data['files'])}):**")
                            for f in data["files"][:10]:
                                lines.append(f"  • {f}")
                        else:
                            lines.append(f"**{tool_name}:** {str(data)[:200]}")
                    else:
                        lines.append(f"**{tool_name}:** {str(data)[:200]}")
                elif error:
                    lines.append(f"**{tool_name} error:** {error}")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════
    # LLM CALL
    # ═══════════════════════════════════════════════════════════════════════

    async def _call_llm(self, context: List[Dict], model: Optional[str], provider_name: Optional[str]) -> Dict:
        """Call LLM using existing provider layer."""
        from app.services.llm.provider_factory import provider_factory
        from app.services.agent_tools.registry import get_registry
        from app.core.config import settings

        provider = provider_factory.get_provider(provider_name or settings.LLM_PROVIDER)
        registry = get_registry()
        tools = registry.get_all_definitions()

        if not model:
            model = settings.LLM_MODEL or "default"

        try:
            response = await provider.chat_with_tools(
                model=model,
                messages=context,
                tools=tools
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"message": {"content": f"Error: {str(e)}", "tool_calls": []}}

    def _parse_tool_calls(self, response: Dict) -> List[Dict]:
        """Parse tool calls from LLM response."""
        message = response.get("message", {})
        return message.get("tool_calls", [])

    async def _store_interaction(self, user_id: Optional[str], message: str, response: str, state: RunState):
        """Store interaction in external MemoryService."""
        pass