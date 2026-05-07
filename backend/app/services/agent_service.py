"""
Production Agent Service - Refactored Architecture

Uses isolated components:
- CoreAgentLoop: Minimal deterministic core
- ToolExecutor: Independent tool execution
- Side systems: Budget, Convergence, Notifications (external)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.services.tools_service import ToolsService
from app.services.agent_tools import get_registry
from app.services.llm import ChatService
from app.core.config import settings

from app.services.agent_core import (
    CoreAgentLoop,
    ToolExecutor,
    TelegramNotifier,
    BudgetManager,
    ConvergenceAnalyzer,
    MetricsCollector,
)
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

user_service = UserService()


# Default budgets per tool type
DEFAULT_BUDGETS = {
    "web_search": 3,
    "api_fetch": 5,
    "web_fetch": 5,
    "read_file": 10,
    "write_file": 3,
    "edit_file": 3,
    "bash": 10,
    "postgres_query": 5,
    "scrape_and_store": 3,
    "search_stored_content": 5,
    "telegram_send_message": 3,
    "telegram_send_notification": 3,
    "glob": 5,
    "grep": 5,
    "ls": 10,
    "docker": 5,
    "git": 2,
    "pkill": 1,
    "user_write_notes": 3,
    "postgres_list_tables": 3,
    "postgres_describe_table": 3,
    "telegram_bot_health": 3,
    "telegram_get_user_info": 3,
}


class AgentService:
    """
    Refactored Agent Service.

    Architecture:
    - CoreAgentLoop: Pure loop (LLM → Execute → Context)
    - ToolExecutor: Independent tool execution
    - Side systems: BudgetManager, ConvergenceAnalyzer, TelegramNotifier

    All external systems are called BEFORE or AFTER the loop,
    NEVER inside the critical path.
    """

    def __init__(
        self,
        telegram_service=None,
        max_iterations: int = 6,
        max_result_preview: int = 200,
        empty_response_threshold: int = 2,
        convergence_threshold: int = 2,
        tool_timeout: int = 30,
        error_threshold: int = 3,
        max_context_tool_chars: int = 1200,
    ):
        self.telegram_service = telegram_service
        self.max_iterations = max_iterations
        self.max_result_preview = max_result_preview
        self.empty_response_threshold = empty_response_threshold
        self.convergence_threshold = convergence_threshold
        self.tool_timeout = tool_timeout
        self.error_threshold = error_threshold
        self.max_context_tool_chars = max_context_tool_chars

        # Initialize core components
        self.tools_service = ToolsService()
        self.registry = get_registry()
        self.llm = ChatService(
            base_url=settings.OLLAMA_CLOUD_HOST,
            api_key=settings.OLLAMA_API_KEY
        )

        # Initialize tool executor
        self.tool_executor = ToolExecutor(
            tools_service=self.tools_service,
            registry=self.registry,
            default_timeout=self.tool_timeout,
        )

        # Initialize side systems
        self.budget_manager = BudgetManager(DEFAULT_BUDGETS.copy())
        self.convergence_analyzer = ConvergenceAnalyzer(
            threshold=convergence_threshold
        )
        self.metrics = MetricsCollector()

        # Telegram notifier (async worker)
        self.telegram_notifier = TelegramNotifier(
            telegram_service=telegram_service,
            semaphore_limit=5,
        ) if telegram_service else None

    async def run_agent_loop(
        self,
        user_message: str,
        chat_id: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        user_id: Optional[str] = None
    ) -> str:
        """Main entry point for agent execution."""

        # Start telegram notifier worker
        if self.telegram_notifier:
            await self.telegram_notifier.start()

        # Get user's preferred model (if any)
        model = settings.OLLAMA_MODEL
        if user_id:
            model = self._get_user_model(user_id) or model

        logger.info(
            f"AGENT_START: chat_id={chat_id} | "
            f"history_len={len(messages_history)} | tools={len(tools)}"
        )

        # PRE-EXECUTION: Apply budget filtering to tools
        # (This modifies the available tools list, not the tool_calls)
        available_tools = self._filter_tools_by_budget(tools)
        logger.info(f"AGENT: tools_available={len(available_tools)}/{len(tools)}")

        try:
            # Run core loop
            answer, state = await self._run_core_loop(
                user_message=user_message,
                messages_history=messages_history,
                system_prompt=system_prompt,
                tools=available_tools,
                chat_id=chat_id,
                model=model,
            )

            # Log final state
            logger.info(
                f"AGENT_STOP: chat_id={chat_id} | "
                f"iterations={state['iterations']} | "
                f"tools_completed={len(state['completed_tools'])}"
            )

            return answer

        finally:
            # Cleanup
            if self.telegram_notifier:
                await self.telegram_notifier.stop()
            await self.close()

    def _get_user_model(self, user_id: str, db=None) -> Optional[str]:
        """Get user's preferred model from user service."""
        try:
            if db is None:
                from app.models.database import get_db
                db_gen = get_db()
                db = next(db_gen)
            prefs = user_service.get_preferences(db, UUID(user_id))
            return prefs.get("model")
        except Exception:
            return None

    async def _run_core_loop(
        self,
        user_message: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        chat_id: str,
        model: Optional[str] = None,
    ) -> tuple[str, Dict]:
        """Run the minimal core loop with pre/post hooks."""

        context = [
            {"role": "system", "content": system_prompt}
        ]
        context.extend(messages_history[-20:])
        context.append({"role": "user", "content": user_message})

        state = {
            "iterations": 0,
            "tool_history": [],
            "completed_tools": [],
            "failed_tools": [],
        }

        for iteration in range(1, self.max_iterations + 1):
            state["iterations"] = iteration

            # 1. LLM CALL
            response = await self._safe_llm_call(
                model=model or settings.OLLAMA_MODEL,
                messages=context,
                tools=tools
            )

            if response is None:
                return "Service indisponible. Réessayez.", state

            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content", "")

            context.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls
            })

            logger.info(
                f"AGENT_ITERATION: iter={iteration} | "
                f"tools={len(tool_calls)} | content={len(content or '')}"
            )

            # 2. STOP IF NO TOOLS (final answer)
            if not tool_calls:
                if content and content.strip():
                    return content.strip(), state
                continue

            # 3. APPLY BUDGET CHECKING BEFORE EXECUTION
            filtered_calls = self.budget_manager.check(tool_calls)

            if len(filtered_calls) < len(tool_calls):
                logger.warning(
                    f"BUDGET_FILTERED: {len(tool_calls) - len(filtered_calls)} tools"
                )

            # 4. EXECUTE TOOLS
            results = await self.tool_executor.execute_batch(filtered_calls)

            # 5. POST-EXECUTION: Process results
            for tc, result in zip(filtered_calls, results):
                tool_name = tc.get("function", {}).get("name")
                state["tool_history"].append(tool_name)

                if isinstance(result, dict) and result.get("success"):
                    state["completed_tools"].append(tool_name)
                else:
                    state["failed_tools"].append(tool_name)

                summarized = self._summarize_tool_result(result)
                context.append({
                    "role": "tool",
                    "content": summarized,
                    "tool_call_id": tc.get("id")
                })

                # Queue notification (non-blocking)
                if self.telegram_notifier:
                    await self.telegram_notifier.notify(
                        chat_id, tool_name, result
                    )

            # 6. TRIM CONTEXT (single point)
            if len(context) > 30:
                context[:] = context[-30:]

            # 7. POST-EXECUTION: Check convergence
            if self.convergence_analyzer.analyze(
                state["tool_history"],
                results
            ):
                logger.info("CONVERGENCE_DETECTED: stopping")
                return self._format_final_response(state), state

            # 8. POST-EXECUTION: Check error threshold
            if len(state["failed_tools"]) >= self.error_threshold:
                logger.warning(f"ERROR_THRESHOLD: {len(state['failed_tools'])}")
                return "Trop d'erreurs pendant l'exécution.", state

        return "Max iterations reached.", state

    def _filter_tools_by_budget(self, tools: List[Dict]) -> List[Dict]:
        """Filter tools that have exhausted budgets."""
        if not self.budget_manager._budgets:
            return tools

        filtered = []
        for tool in tools:
            name = tool.get("function", {}).get("name")
            if name in self.budget_manager._budgets:
                if self.budget_manager._budgets[name] > 0:
                    filtered.append(tool)
                # Skip exhausted budget tools
            else:
                filtered.append(tool)
        return filtered

    async def _safe_llm_call(self, model: str, **kwargs):
        """LLM call with single retry on timeout."""
        try:
            return await asyncio.wait_for(
                self.llm.chat_with_tools(model=model, **kwargs),
                timeout=60
            )
        except asyncio.TimeoutError:
            logger.warning("LLM timeout, retrying...")
            try:
                return await asyncio.wait_for(
                    self.llm.chat_with_tools(model=model, **kwargs),
                    timeout=60
                )
            except asyncio.TimeoutError:
                logger.error("LLM timeout after 2 attempts")
                return None
        except Exception as e:
            logger.warning(f"LLM error with model {model}: {e}")
            # Fallback to default model on error
            if model != settings.OLLAMA_MODEL:
                logger.info(f"Falling back to default model {settings.OLLAMA_MODEL}")
                try:
                    return await asyncio.wait_for(
                        self.llm.chat_with_tools(
                            model=settings.OLLAMA_MODEL,
                            **kwargs
                        ),
                        timeout=60
                    )
                except Exception:
                    return None
            return None

    def _summarize_tool_result(self, result: Any) -> str:
        """Lightweight result summarization."""
        import re
        from app.services.agent_tools.tools.base_tool import ToolResult
        if isinstance(result, ToolResult):
            if result.error:
                text = f"Error: {result.error}"
            elif result.data:
                if isinstance(result.data, dict):
                    if "stdout" in result.data:
                        text = result.data["stdout"]
                    elif "response" in result.data:
                        text = result.data["response"]
                    else:
                        text = str(result.data)
                else:
                    text = str(result.data)
            else:
                text = "Done"
        else:
            text = str(result)

        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > self.max_context_tool_chars:
            text = text[:self.max_context_tool_chars] + "... [truncated]"
        return text

    def _format_final_response(self, state: Dict) -> str:
        """Format final response from state."""
        known = state.get("completed_tools", [])
        if known:
            return f"Résultats après {state['iterations']} étapes: {', '.join(known[-5:])}"
        return "Je n'ai pas pu terminer la tâche."

    async def close(self):
        """Cleanup resources."""
        await self.llm.close()