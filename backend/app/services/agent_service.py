"""
Agent Service

Handles agent loop with iterative tool calls and user notifications.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from app.services.tools_service import ToolsService
from app.services.agent_tools import get_registry
from app.services.llm import ChatService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agent service that handles iterative tool calling with user notifications.

    Flow:
    1. LLM decides to call tools
    2. Execute each tool and notify user via Telegram
    3. Check stop conditions with heuristics
    4. When done, return final response
    """

    def __init__(
        self,
        telegram_service=None,
        max_iterations: int = 10,
        max_result_preview: int = 200,
        empty_response_threshold: int = 2,
        convergence_threshold: int = 3
    ):
        """
        Initialize agent service.

        Args:
            telegram_service: Telegram service for notifications (optional)
            max_iterations: Max tool call iterations
            max_result_preview: Max chars to send to user per result
            empty_response_threshold: Consecutive empty responses before stop
            convergence_threshold: Similar results before stop
        """
        self.telegram_service = telegram_service
        self.max_iterations = max_iterations
        self.max_result_preview = max_result_preview
        self.empty_response_threshold = empty_response_threshold
        self.convergence_threshold = convergence_threshold
        self.tools_service = ToolsService()
        self.registry = get_registry()
        self.llm = ChatService(
            base_url=settings.OLLAMA_CLOUD_HOST,
            api_key=settings.OLLAMA_API_KEY
        )

    async def run_agent_loop(
        self,
        user_message: str,
        chat_id: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        user_id: str = None
    ) -> str:
        """
        Run agent loop with notifications.

        Args:
            user_message: The user's message
            chat_id: Telegram chat ID for notifications
            messages_history: Conversation history
            system_prompt: System prompt to use
            tools: Tool definitions for LLM
            user_id: User ID for preferences

        Returns:
            Final response to send to user
        """
        context = [{"role": "system", "content": system_prompt}]
        context.extend(messages_history[-20:])
        context.append({"role": "user", "content": user_message})

        print(f"AGENT: Starting loop, context_len={len(context)}, tools={len(tools)}", flush=True)

        iteration = 0
        consecutive_empty = 0
        previous_result_hash = None
        similar_results_count = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"AGENT: Iteration {iteration}", flush=True)

            response = await self.llm.chat_with_tools(
                model=settings.OLLAMA_MODEL,
                messages=context,
                tools=tools
            )
            print(f"AGENT: LLM response received", flush=True)

            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content", "")

            if tool_calls:
                consecutive_empty = 0
                similar_results_count = 0

                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name")
                    arguments = func.get("arguments", {})

                    result = await self._execute_tool(tool_name, arguments)

                    if self.telegram_service:
                        await self._notify_result(chat_id, tool_name, result)

                    context.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call.get("id")
                    })

                previous_result_hash = self._hash_result(result)
            else:
                stop_reason = self._determine_stop_reason(
                    content=content,
                    iteration=iteration,
                    consecutive_empty=consecutive_empty,
                    previous_result_hash=previous_result_hash,
                    similar_count=similar_results_count
                )

                if stop_reason:
                    print(f"AGENT: Stopping - {stop_reason}", flush=True)
                    return self._format_final_response(content, iteration)

                if content:
                    return content

                consecutive_empty += 1
                print(f"AGENT: Empty response #{consecutive_empty}", flush=True)
                if consecutive_empty >= self.empty_response_threshold:
                    print(f"AGENT: Too many empty responses, stopping", flush=True)
                    return "Here's what I found."

        print(f"AGENT: max iterations reached, returning fallback", flush=True)
        return "Here's what I found."

    def _determine_stop_reason(
        self,
        content: str,
        iteration: int,
        consecutive_empty: int,
        previous_result_hash: Optional[int],
        similar_count: int
    ) -> Optional[str]:
        """
        Determine if loop should stop based on heuristics.

        Returns:
            Stop reason string if should stop, None otherwise
        """
        if self._is_completion_signal(content):
            return "completion_signal"

        if consecutive_empty >= self.empty_response_threshold:
            return f"empty_responses_{consecutive_empty}"

        if iteration >= self.max_iterations:
            return "max_iterations"

        return None

    def _is_completion_signal(self, content: str) -> bool:
        """
        Detect if content indicates the task is complete.

        Heuristic patterns:
        - Direct answers with specific info
        - Summary phrases
        - Conclusion markers
        """
        if not content or len(content.strip()) < 10:
            return False

        content_lower = content.lower().strip()

        completion_patterns = [
            r"^(here'?s?|the answer is|answer:|summary:|in summary)",
            r"^(i (can'?t|don'?t) know|i'?m not sure|i cannot)",
            r"(that'?s all|that was|this should|this will help)",
            r"^(no (further|more) |no additional)",
        ]

        for pattern in completion_patterns:
            if re.match(pattern, content_lower):
                return True

        if len(content) > 100 and any(marker in content_lower for marker in [
            "here's what", "based on the", "according to", "the result",
            "the information", "as shown", "as you can see"
        ]):
            return True

        return False

    def _is_new_information(self, new_result: Any, previous_results: List[str]) -> bool:
        """
        Detect if new result contains genuinely new information.

        Args:
            new_result: The new tool result
            previous_results: List of previous result strings

        Returns:
            True if result contains new info, False if redundant
        """
        new_str = str(new_result).lower()

        stop_words = [
            "error", "failed", "unknown tool", "not found",
            "permission denied", "connection refused"
        ]
        if any(word in new_str for word in stop_words):
            return True

        for prev in previous_results[-3:]:
            prev_lower = prev.lower()

            if new_str == prev_lower:
                return False

            similarity = self._calculate_text_similarity(new_str, prev_lower)
            if similarity > 0.85:
                return False

        return True

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple similarity between two texts.

        Returns:
            Float between 0 and 1 where 1 is identical
        """
        if text1 == text2:
            return 1.0

        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _hash_result(self, result: Any) -> int:
        """
        Create a simple hash of a result for convergence detection.
        """
        result_str = str(result).lower()
        return sum(ord(c) for c in result_str if c.isalnum()) % 10000

    def _format_final_response(self, content: str, iterations: int) -> str:
        """
        Format the final response before returning.

        Args:
            content: The content to format
            iterations: Number of iterations used

        Returns:
            Formatted response string
        """
        stripped = content.strip() if content else ""
        if stripped:
            return stripped

        if iterations > 5:
            return f"Task completed after {iterations} steps."

        return "Here's what I found."

    async def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute a tool using ToolsService or Agent registry."""
        try:
            result = await self.tools_service.execute_tool(tool_name, arguments)
            if not (isinstance(result, dict) and "Unknown tool" in str(result.get("error", ""))):
                return result
        except Exception:
            pass

        result = await self.registry.execute(tool_name, **arguments)
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error
        }

    async def _notify_result(self, chat_id: str, tool_name: str, result: Any) -> None:
        """Send tool result notification to user."""
        if not self.telegram_service:
            return

        if isinstance(result, dict):
            success = result.get("success", False)
            error = result.get("error")
            data = result.get("data")
        else:
            success = getattr(result, 'success', False)
            error = getattr(result, 'error', None)
            data = getattr(result, 'data', None)

        if error:
            await self.telegram_service.send_message(
                chat_id,
                f"❌ {tool_name}: {str(error)[:self.max_result_preview]}"
            )
        elif data is not None:
            preview = str(data)[:self.max_result_preview]
            if len(str(data)) > self.max_result_preview:
                preview += "..."
            await self.telegram_service.send_message(
                chat_id,
                f"✓ {tool_name}: {preview}"
            )
        else:
            await self.telegram_service.send_message(
                chat_id,
                f"✓ {tool_name}: Done"
            )

    async def _should_continue_loop(self, context: List[Dict], iteration: int) -> bool:
        """Ask LLM if more tools are needed."""
        if iteration >= self.max_iterations:
            return False

        try:
            eval_message = {
                "role": "user",
                "content": "Based on the tool results above, can you answer the user's original question? "
                          "Answer YES if you have all the information needed, NO if you need more tools."
            }

            eval_context = list(context) + [eval_message]

            response = await self.llm.chat(
                model=settings.OLLAMA_MODEL,
                messages=eval_context,
                options={"temperature": 0.1}
            )

            content = response.get("message", {}).get("content", "").upper()

            if "NO" in content and "YES" not in content:
                return True

            return False

        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            return False

    async def _generate_summary(self, context: List[Dict], original_question: str) -> str:
        """Generate final summary from tool results."""
        try:
            summary_message = {
                "role": "user",
                "content": f"User asked: '{original_question}'\n\n"
                           f"The tool results have been collected. "
                           f"Provide a clear, concise summary of the findings. "
                           f"IMPORTANT: Do not invent data - only use what the tools returned."
            }

            summary_context = list(context) + [summary_message]

            response = await self.llm.chat(
                model=settings.OLLAMA_MODEL,
                messages=summary_context,
                options={"temperature": 0.3}
            )

            return response.get("message", {}).get("content", "Here's what I found...")

        except Exception as e:
            logger.error(f"Summary error: {e}")
            return "Here's what I found from the tools."

    async def close(self):
        """Close LLM client."""
        await self.llm.close()