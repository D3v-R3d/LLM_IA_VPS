"""
Minimal Agent Runner

A simple stateless agent loop that:
1. Calls LLM
2. Parses response
3. Executes tools if needed
4. Returns final answer

The loop should NOT manage:
- Telegram
- Sessions
- Database
- Retries
- Notifications
- Memory compression
"""

import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from agent execution."""
    text: str
    success: bool = True
    iterations: int = 0
    completed_tools: List[str] = None

    def __post_init__(self):
        if self.completed_tools is None:
            self.completed_tools = []


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool: str
    success: bool
    data: Any = None
    error: Optional[str] = None


class AgentRunner:
    """
    Minimal stateless agent runner.

    Simple loop:
    while steps < max_steps:
        response = llm()
        if no_tool_calls:
            return response
        result = execute_tool()
        append_context()

    Does NOT handle:
    - Telegram
    - Sessions
    - Database
    - Retries
    - Notifications
    - Memory compression
    """

    def __init__(
        self,
        llm,
        tool_executor,
        max_steps: int = 10,
        max_context: int = 30,
        max_tool_chars: int = 1200,
        llm_timeout: int = 60,
    ):
        self._llm = llm
        self._executor = tool_executor
        self._max_steps = max_steps
        self._max_context = max_context
        self._max_tool_chars = max_tool_chars
        self._llm_timeout = llm_timeout

    async def run(
        self,
        user_message: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        chat_id: str,
        user_id: Optional[str] = None,
        model: str = "gemma4:31b",
    ) -> str:
        """
        Run the agent loop and return the final response text.

        Args:
            user_message: The user's message
            messages_history: Previous messages in conversation
            system_prompt: System prompt to use
            tools: Available tool definitions
            chat_id: Telegram chat ID
            user_id: User ID for preferences
            model: Model to use

        Returns:
            Final response text
        """
        context = [
            {"role": "system", "content": system_prompt}
        ]
        context.extend(messages_history[-20:])
        context.append({"role": "user", "content": user_message})

        state = {
            "iterations": 0,
            "completed_tools": [],
            "failed_tools": [],
        }

        for iteration in range(1, self._max_steps + 1):
            state["iterations"] = iteration

            response = await self._call_llm(context, tools, model)
            if response is None:
                return "Service indisponible. Réessayez."

            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content", "")

            if not tool_calls and content:
                tool_calls = self._extract_json_tool_calls(content)
                if tool_calls:
                    content = ""
                    logger.warning(f"TOOL_CALLS_EXTRACTED_FROM_CONTENT: {tool_calls}")

            context.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls
            })

            logger.info(f"AgentRunner: iter={iteration}, tools={len(tool_calls)}, content_len={len(content or '')}")

            if not tool_calls:
                if content and content.strip():
                    return content.strip()
                continue

            results = await self._executor.execute_batch(tool_calls)

            for tc, result in zip(tool_calls, results):
                tool_name = tc.get("function", {}).get("name")

                if isinstance(result, dict) and result.get("success"):
                    state["completed_tools"].append(tool_name)
                else:
                    state["failed_tools"].append(tool_name)

                summarized = self._summarize_result(result)
                context.append({
                    "role": "tool",
                    "content": summarized,
                    "tool_call_id": tc.get("id")
                })

            context = self._trim_context(context)

        return "Max iterations reached."

    async def _call_llm(
        self,
        context: List[Dict],
        tools: List[Dict],
        model: str,
    ) -> Optional[Dict]:
        """Make LLM call with timeout."""
        try:
            return await asyncio.wait_for(
                self._llm.chat_with_tools(model=model, messages=context, tools=tools),
                timeout=self._llm_timeout
            )
        except asyncio.TimeoutError:
            logger.error("LLM timeout in AgentRunner")
            return None
        except Exception as e:
            logger.exception(f"LLM error: {e}")
            return None

    def _trim_context(self, context: List[Dict]) -> List[Dict]:
        """Trim context to max size."""
        if len(context) > self._max_context:
            context[:] = context[-self._max_context:]
        return context

    def _summarize_result(self, result: Any) -> str:
        """Summarize tool result for context."""
        if isinstance(result, dict):
            if result.get("error"):
                text = f"Error: {result['error']}"
            elif result.get("data"):
                data = result["data"]
                if isinstance(data, dict):
                    if "stdout" in data:
                        text = data["stdout"]
                    elif "response" in data:
                        text = data["response"]
                    else:
                        text = str(data)
                else:
                    text = str(data)
            else:
                text = "Done"
        else:
            text = str(result)

        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > self._max_tool_chars:
            text = text[:self._max_tool_chars] + "... [truncated]"
        return text

    def _extract_json_tool_calls(self, content: str) -> List[Dict]:
        """Extract tool calls from JSON content in markdown code blocks or raw JSON."""
        if not content:
            return []

        tool_calls = []

        json_block_pattern = r'```json\s*(.+?)\s*```'
        matches = re.findall(json_block_pattern, content, re.DOTALL)
        for match in matches:
            tool_calls = self._try_parse_tool_calls(match)
            if tool_calls:
                logger.info(f"Extracted {len(tool_calls)} tool_calls from JSON block")
                break

        if not tool_calls:
            code_block_pattern = r'```\s*(.+?)\s*```'
            matches = re.findall(code_block_pattern, content, re.DOTALL)
            for match in matches:
                tool_calls = self._try_parse_tool_calls(match)
                if tool_calls:
                    logger.info(f"Extracted {len(tool_calls)} tool_calls from code block")
                    break

        if not tool_calls and content.strip().startswith("{"):
            tool_calls = self._try_parse_tool_calls(content)

        return tool_calls

    def _try_parse_tool_calls(self, content: str) -> List[Dict]:
        """Try to parse tool_calls from content, handling malformed JSON."""
        try:
            parsed = json.loads(content.strip())
            if "tool_calls" in parsed:
                return self._normalize_tool_calls(parsed["tool_calls"])
        except json.JSONDecodeError:
            pass

        tool_calls = []
        func_pattern = r'"function"\s*:\s*\{[^}]+\}'
        matches = re.findall(func_pattern, content)
        for match in matches:
            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', match)
            args_match = re.search(r'"arguments"\s*:\s*(".*?"|\{[^}]+\})', match)

            if name_match:
                name = name_match.group(1)
                arguments = {}

                if args_match:
                    args_str = args_match.group(1)
                    if args_str.startswith('{'):
                        try:
                            arguments = json.loads(args_str)
                        except:
                            try:
                                arguments = json.loads(args_str.replace('\\"', '"').replace('"', '"'))
                            except:
                                arguments = {"raw": args_str}
                    else:
                        try:
                            arguments = json.loads(args_str)
                        except:
                            arguments = {"raw": args_str}

                tool_calls.append({
                    "function": {
                        "name": name,
                        "arguments": arguments
                    }
                })

        return tool_calls

    def _normalize_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Normalize tool calls, fixing arguments that are JSON strings."""
        normalized = []
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            arguments = func.get("arguments", {})

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    try:
                        arguments = json.loads(arguments.replace('\\"', '"'))
                    except json.JSONDecodeError:
                        arguments = {"raw": arguments}

            normalized.append({
                "function": {
                    "name": name,
                    "arguments": arguments
                },
                "id": tc.get("id", ""),
                "type": tc.get("type", "function")
            })

        return normalized