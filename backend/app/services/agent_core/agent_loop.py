"""
Minimal deterministic core agent loop.
NO side effects, NO notifications, NO budgets inside loop.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


class CoreAgentLoop:
    """
    Pure core loop - ONLY handles:
    1. LLM calls
    2. Tool execution
    3. Context management
    4. Iteration control

    All side systems (budget, notifications, convergence) are EXTERNAL.
    """

    def __init__(
        self,
        llm,
        tool_executor,
        max_iterations: int = 3,
        max_context: int = 30,
        llm_timeout: int = 60,
        max_tool_chars: int = 1200,
    ):
        self.llm = llm
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations
        self.max_context = max_context
        self.llm_timeout = llm_timeout
        self.max_tool_chars = max_tool_chars

    async def run(
        self,
        system_prompt: str,
        messages_history: List[Dict],
        user_message: str,
        tools: List[Dict],
        model: str = "minimax-m2.7",
    ) -> Tuple[str, Dict]:
        """
        Returns: (answer, execution_state)
        """
        self._model = model
        # BUILD INITIAL CONTEXT
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

        # MAIN LOOP - Minimal and deterministic
        for iteration in range(1, self.max_iterations + 1):
            state["iterations"] = iteration

            # 1. LLM CALL
            response = await self._call_llm(context, tools)
            if response is None:
                logger.error("LLM call failed after retries")
                return "Service temporairement indisponible.", state

            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content", "")

            # 2. APPEND ASSISTANT RESPONSE
            context.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls
            })

            logger.info(
                f"LOOP: iter={iteration} | tools={len(tool_calls)} | "
                f"content_len={len(content or '')}"
            )

            # 3. STOP IF NO TOOLS
            if not tool_calls:
                if content and content.strip():
                    logger.info(f"LOOP STOP: final_answer | iter={iteration}")
                    return content.strip(), state
                # Empty response - continue to next iteration
                continue

            # 4. EXECUTE TOOLS
            results = await self.tool_executor.execute_batch(tool_calls)

            # 5. APPEND RESULTS TO CONTEXT
            for tc, result in zip(tool_calls, results):
                tool_name = tc.get("function", {}).get("name")
                state["tool_history"].append(tool_name)

                if isinstance(result, dict) and result.get("success"):
                    state["completed_tools"].append(tool_name)
                else:
                    state["failed_tools"].append(tool_name)

                summarized = self._summarize(result)
                context.append({
                    "role": "tool",
                    "content": summarized,
                    "tool_call_id": tc.get("id")
                })

            # 6. TRIM CONTEXT (single point)
            context = self._trim_context(context)

        logger.warning(f"LOOP STOP: max_iterations={self.max_iterations}")
        return "Max iterations reached.", state

    async def _call_llm(
        self,
        context: List[Dict],
        tools: List[Dict]
    ) -> Optional[Dict]:
        try:
            return await asyncio.wait_for(
                self.llm.chat_with_tools(
                    model=self._model,
                    messages=context,
                    tools=tools
                ),
                timeout=self.llm_timeout
            )
        except asyncio.TimeoutError:
            logger.error("LLM timeout")
            return None
        except Exception as e:
            logger.exception(f"LLM error: {e}")
            return None

    def _trim_context(self, context: List[Dict]) -> List[Dict]:
        """Single context trim point - in-place for efficiency."""
        if len(context) > self.max_context:
            context[:] = context[-self.max_context:]
        return context

    def _summarize(self, result: Any) -> str:
        """Lightweight result summarization."""
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
        if len(text) > self.max_tool_chars:
            text = text[:self.max_tool_chars] + "... [truncated]"
        return text