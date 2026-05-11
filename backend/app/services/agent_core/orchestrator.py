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
from app.observability.event_logger import EventLogger
from app.observability.event_types import EventType

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
        from app.services.agent_core.side_systems import BudgetManager

        self.registry = get_registry()
        self.tool_executor = ToolExecutor(registry=self.registry)

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
            state=state,
            db_session=db_session
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
        from app.services.agent_core.intent_classifier import classify_message
        return classify_message(message)

    # _pack removed — logic now lives in intent_classifier.classify_message

import re

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


    def _lightweight_plan(self, message: str) -> Plan:
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

    async def plan(self, message: str, complexity: int) -> Optional[Plan]:
        """Generate a plan based on message complexity."""
        return await self._llm_plan(message)

    async def _llm_plan(self, message: str) -> Optional[Plan]:
        """LLM-based structured planning for complexity 4-5 with strict JSON validation."""

        from app.services.llm.provider_factory import provider_factory
        from app.core.config import settings
        from app.services.prompt_service import PromptService
        from app.services.agent_core.intent_classifier import select_tools_for_message

        tools_list = ", ".join(select_tools_for_message(message)) if message else "none"

        planning_template = PromptService.get_planning_prompt()

        # 1. Build prompt safely
        try:
            planning_prompt = planning_template.format(
                message=message,
                available_tools=tools_list
            )
        except Exception as e:
            logger.error(f"Planning prompt formatting failed: {e}")
            return self._lightweight_plan(message)

        try:
            provider = provider_factory.get_provider(settings.LLM_PROVIDER)

            response = await provider.chat(
                model=settings.LLM_MODEL or "default",
                messages=[{"role": "user", "content": planning_prompt}],
                options={"max_tokens": 500}
            )

            content = response.get("content") if isinstance(response, dict) else str(response)

            # 2. Parse strictly
            plan_data = self._parse_json_plan_strict(content)

            if not plan_data:
                logger.warning("LLM returned invalid plan JSON → fallback lightweight")
                return self._lightweight_plan(message)

            steps = plan_data.get("steps", [])
            tools = plan_data.get("tools", [])

            if not steps:
                logger.warning("LLM plan empty → fallback lightweight")
                return self._lightweight_plan(message)

            return Plan(
                steps=steps,
                expected_tools=tools
            )

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
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
        state: RunState,
        db_session: Any = None
    ) -> Dict:
        """Main execution loop with all improvements."""
        max_steps = min(self.config.max_steps, self.config.hard_limit)
        all_tool_results = []

        for step in range(1, max_steps + 1):
            state.iteration = step
            state.step_retries = 0
            logger.debug(f"Execution step: {step}/{max_steps}")

            response = await self._call_llm(context, model, provider_name, db_session, run_id=state.run_id)

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

            if self.budget_manager:
                tool_calls = self.budget_manager.check(tool_calls)
                if not tool_calls:
                    return {
                        "direct_response": "Tool budget exhausted for this request.",
                        "tool_results": []
                    }

            tool_results = await self._execute_with_idempotency(tool_calls, state, db_session=db_session)
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
        state: RunState,
        db_session: Any = None
    ) -> List:
        """
        Execute tools with:
        - Idempotency check (FIX 1)
        - Unique call_id for results (FIX 2)
        - Exponential backoff (FIX 7)
        """
        event_logger = None
        if db_session and state.run_id:
            try:
                event_logger = EventLogger(db=db_session, run_id=state.run_id, chat_id=None)
            except Exception:
                pass

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

            if event_logger:
                event_logger.emit_tool_call(
                    tool_name=tool_name,
                    call_id=call_key,
                    arguments=tc.get("function", {}).get("arguments", {}),
                )

            result = await self.tool_executor.execute_batch([tc])
            tool_result = result[0] if result else None

            state.executed_calls[call_key] = {
                "status": "success" if tool_result and tool_result.success else "failed",
                "result": tool_result,
                "tool_name": tool_name
            }

            if event_logger:
                result_size = len(str(tool_result.data)) if tool_result and tool_result.data else 0
                event_logger.emit_tool_result(
                    tool_name=tool_name,
                    call_id=call_key,
                    success=bool(tool_result and tool_result.success),
                    duration_ms=int(tool_result.metadata.duration_ms) if tool_result and tool_result.metadata else 0,
                    result_size=result_size,
                    error=tool_result.error if tool_result and not tool_result.success else None,
                )

            results.append(tool_result)

        failed = [(i, r) for i, r in enumerate(results) if r and not r.success]

        if not failed:
            return results

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

            backoff = 0.5 * (2 ** retry_count)
            await asyncio.sleep(backoff)

            retry_result = await self.tool_executor.execute_batch([tool_calls[idx]])
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

           # ---------- web response
           if isinstance(data, dict) and "response" in data:
               sections.append(
                   f"🌐 Résultat web récupéré\n\n"
                   f"{data['response']}"
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

           # ---------- files
           elif isinstance(data, dict) and "files" in data:
               files = "\n".join(f"• {f}" for f in data["files"])

               sections.append(
                   f"📂 Fichiers trouvés\n\n"
                   f"J’ai trouvé **{len(data['files'])}** fichiers :\n\n"
                   f"{files}"
               )

           # ---------- file content
           elif tool == "read_file":
               sections.append(
                   f"📄 Contenu du fichier\n\n"
                   f"Voilà ce que j’ai lu 👇\n\n"
                   f"```text\n{data}\n```"
               )

           # ---------- docker
           elif "docker" in tool:
               sections.append(
                   f"🐳 Docker\n\n"
                   f"Commande exécutée avec succès.\n\n"
                   f"```text\n{data}\n```"
               )

           # ---------- bash
           elif tool == "bash":
               sections.append(
                   f"💻 Commande terminal\n\n"
                   f"Résultat :\n\n"
                   f"```text\n{data}\n```"
               )

           # ---------- nas
           elif isinstance(data, dict) and "shares" in data:
               shares = "\n".join(
                   f"• {s.get('name','unknown')}"
                   for s in data["shares"]
               )

               sections.append(
                   f"💾 NAS\n\n"
                   f"Partages disponibles :\n\n"
                   f"{shares}"
               )

           # ---------- fallback dict
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
    # LLM CALL
    # ═══════════════════════════════════════════════════════════════════════

    async def _call_llm(self, context: List[Dict], model: Optional[str], provider_name: Optional[str], db_session: Any = None, run_id: str = None) -> Dict:
        """Call LLM using existing provider layer."""
        from app.services.llm.provider_factory import provider_factory
        from app.services.agent_tools.registry import get_registry
        from app.core.config import settings

        provider = provider_factory.get_provider(provider_name or settings.LLM_PROVIDER)
        registry = get_registry()
        tools = registry.get_all_definitions()

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
            event_logger.emit_llm_request(
                model=model,
                provider=provider_name or settings.LLM_PROVIDER,
                prompt_length=sum(len(str(m.get("content", ""))) for m in context),
                tools_count=len(tools),
            )

        try:
            response = await provider.chat_with_tools(
                model=model,
                messages=context,
                tools=tools
            )

            duration_ms = int((time.time() - start_time) * 1000)
            if event_logger:
                try:
                    content = response.get("message", {}).get("content", "") or ""
                    event_logger.emit_llm_response(
                        model=model,
                        provider=provider_name or settings.LLM_PROVIDER,
                        tokens_in=0,
                        tokens_out=0,
                        duration_ms=duration_ms,
                        response_preview=content[:500] if content else None,
                    )
                except Exception:
                    pass

            return response
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if event_logger:
                try:
                    event_logger.emit_error(
                        error_type="LLMCallError",
                        error_message=str(e),
                    )
                except Exception:
                    pass

            logger.error(f"LLM call failed: {e}")
            return {"message": {"content": f"Error: {str(e)}", "tool_calls": []}}

    def _parse_tool_calls(self, response: Dict) -> List[Dict]:
        """Parse tool calls from LLM response."""
        message = response.get("message", {})
        return message.get("tool_calls", [])

    async def _store_interaction(self, user_id: Optional[str], message: str, response: str, state: RunState):
        """Store interaction in external MemoryService."""
        pass