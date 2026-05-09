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
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

from app.services.agent_core.side_systems import BudgetManager
from app.services.llm_logger import LlmLogger

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Minimal stateless agent runner.

    Supports per-user provider routing via provider_factory.
    Falls back to the default LLM passed at init when no provider_name given.

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
        max_steps: int = 5,
        max_context: int = 30,
        max_tool_chars: int = 1200,
        llm_timeout: int = 200,
        budgets: Optional[Dict[str, int]] = None,
        provider_factory=None,
    ):
        self._llm = llm
        self._executor = tool_executor
        self._max_steps = max_steps
        self._last_llm_error = None
        self._max_context = max_context
        self._max_tool_chars = max_tool_chars
        self._llm_timeout = llm_timeout
        self._budgets = BudgetManager(budgets or {})
        self._provider_factory = provider_factory

    def _get_llm(self, provider_name: Optional[str] = None):
        """Get the right LLM provider: per-user if specified, else default."""
        if provider_name and self._provider_factory:
            return self._provider_factory.get_provider(provider_name)
        return self._llm

    async def _get_default_model(self, provider_name: Optional[str] = None) -> str:
        """Get default model from provider's available models."""
        llm = self._get_llm(provider_name)
        prov_name = provider_name or llm.name
        known_models = {
            "google": "gemma-4-31b-it",
            "groq": "llama-3.1-8b-instant",
            "ollama": "qwen2.5:3b",
        }
        if prov_name in known_models:
            return known_models[prov_name]

        try:
            logger.info("Fetching available models from provider")
            models = await llm.list_models()
            logger.info(f"Got {len(models)} models")

            for m in models:
                if isinstance(m, dict):
                    model_id = m.get("id") or m.get("name") or m.get("model", "")
                    logger.info(f"Checking model: {model_id}")
                    if model_id and "prompt-guard" not in model_id.lower():
                        logger.info(f"Selected model: {model_id}")
                        return model_id
                elif m and "prompt-guard" not in str(m).lower():
                    return str(m)
        except Exception as e:
            logger.error(f"_get_default_model error: {e}")

        # Fallback to known working model
        logger.info("Using fallback model")
        return known_models.get(prov_name, "gemma-4-31b-it")

    async def run(
        self,
        user_message: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        chat_id: str,
        user_id: Optional[str] = None,
        model: str = None,
        provider_name: Optional[str] = None,
        db_session=None,
        conversation_id: Optional[uuid.UUID] = None,
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
            provider_name: Provider for this user (None = default)
            db_session: Database session for logging
            conversation_id: Conversation UUID for logging

        Returns:
            Final response text
        """
        start_time = time.time()
        llm_logger = None
        log_id = None
        user_uuid = uuid.UUID(user_id) if user_id else None

        if db_session:
            llm_logger = LlmLogger(db_session)
            log_id = llm_logger.log_request(
                message=user_message,
                model=model or "unknown",
                provider=llm.name if (llm := self._get_llm(provider_name)) else "unknown",
                user_id=user_uuid,
                conversation_id=conversation_id,
                chat_id=chat_id,
                tools_sent=[t.get("function", {}).get("name") for t in tools] if tools else [],
            )

        if not model:
            model = await self._get_default_model(provider_name)

        if not model:
            return "Aucun modèle disponible."

        llm = self._get_llm(provider_name)
        logger.info(f"AgentRunner using provider={llm.name} model={model}")

        context = [
            {"role": "system", "content": system_prompt}
        ]
        context.extend(messages_history[-20:])
        context.append({"role": "user", "content": user_message})

        state = {
            "iterations": 0,
            "completed_tools": [],
            "failed_tools": [],
            "last_tool_calls": [],
        }

        for iteration in range(1, self._max_steps + 1):
            state["iterations"] = iteration

            response = await self._call_llm(context, tools, model, llm)
            if response is None:
                if llm_logger and log_id:
                    duration_ms = int((time.time() - start_time) * 1000)
                    error_info = self._last_llm_error or {}
                    llm_logger.log_response(
                        log_id=log_id,
                        response_text="",
                        success=False,
                        error=error_info.get("error", "LLM returned None"),
                        error_code=error_info.get("error_code"),
                        error_body=error_info.get("error_body"),
                        duration_ms=duration_ms,
                    )
                return "Service indisponible. Réessayez."

            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content", "")

            # Extract tool calls from raw content (before cleaning)
            raw_content = content
            if not tool_calls and raw_content:
                tool_calls = self._extract_json_tool_calls(raw_content)
                if tool_calls:
                    content = ""
                    logger.warning(f"TOOL_CALLS_EXTRACTED_FROM_CONTENT: {tool_calls}")

            # Clean content for context and final response (remove thought/tool_code tags)
            cleaned_content = self.clean_response_content(content)

            context.append({
                "role": "assistant",
                "content": cleaned_content or "",
                "tool_calls": tool_calls
            })

            logger.info(f"AgentRunner: iter={iteration}, tools={len(tool_calls)}, content_len={len(cleaned_content or '')}")

            if not tool_calls:
                if cleaned_content and cleaned_content.strip():
                    if llm_logger and log_id:
                        duration_ms = int((time.time() - start_time) * 1000)
                        llm_logger.log_response(
                            log_id=log_id,
                            response_text=cleaned_content.strip(),
                            tool_calls=state.get("last_tool_calls", []),
                            iterations=state["iterations"],
                            duration_ms=duration_ms,
                            success=True,
                        )
                    return cleaned_content.strip()
                continue

            # Budget check: filter out exhausted tools
            tool_calls = self._budgets.check(tool_calls)
            state["last_tool_calls"] = tool_calls

            if not tool_calls:
                logger.warning("All tool calls filtered by budget, returning")
                exhausted = self._budgets.get_exhausted_tools()
                if exhausted:
                    context.append({
                        "role": "tool",
                        "content": f"Tools exhausted: {', '.join(exhausted)}. Try a different approach."
                    })
                    continue
                if llm_logger and log_id:
                    duration_ms = int((time.time() - start_time) * 1000)
                    llm_logger.log_response(
                        log_id=log_id,
                        response_text=cleaned_content.strip() if cleaned_content else "",
                        tool_calls=[],
                        iterations=state["iterations"],
                        duration_ms=duration_ms,
                        success=True,
                    )
                return content.strip() if content else "Tools budget exhausted."

            results = await self._executor.execute_batch(tool_calls)

            for tc, result in zip(tool_calls, results):
                tool_name = tc.get("function", {}).get("name")

                if isinstance(result, dict):
                    # Legacy dict result (backward compat)
                    if result.get("success"):
                        state["completed_tools"].append(tool_name)
                    else:
                        state["failed_tools"].append(tool_name)
                    summarized = self._summarize_result(result)
                else:
                    # ToolResponse object
                    if result.success:
                        state["completed_tools"].append(tool_name)
                    else:
                        state["failed_tools"].append(tool_name)
                    summarized = result.summary

                context.append({
                    "role": "tool",
                    "content": summarized,
                    "tool_call_id": tc.get("id")
                })

            context = self._trim_context(context)

        if llm_logger and log_id:
            duration_ms = int((time.time() - start_time) * 1000)
            llm_logger.log_response(
                log_id=log_id,
                response_text="Max iterations reached",
                tool_calls=state.get("last_tool_calls", []),
                iterations=state["iterations"],
                duration_ms=duration_ms,
                success=True,
            )
        return "Max iterations reached."

    async def _call_llm(
        self,
        context: List[Dict],
        tools: List[Dict],
        model: str,
        llm=None,
    ) -> Optional[Dict]:
        """Make LLM call with timeout and retry for rate limits."""
        llm = llm or self._llm
        max_retries = 2
        retry_delay = 60
        logger.info(f"LLM call: provider={llm.name} model={model}, tools={len(tools)}")

        last_error = None
        for attempt in range(max_retries):
            try:
                cleaned_tools = self.strip_internal_tool_fields(tools)
                return await asyncio.wait_for(
                    llm.chat_with_tools(model=model, messages=context, tools=cleaned_tools),
                    timeout=self._llm_timeout
                )
            except asyncio.TimeoutError:
                logger.error("LLM timeout in AgentRunner")
                last_error = {"error": "Timeout", "error_code": "timeout"}
                return None
            except Exception as e:
                error_str = str(e)
                last_error = {
                    "error": error_str[:500],
                    "error_code": self._extract_status_code(error_str),
                    "error_body": self._extract_error_body(error_str),
                }
                if "429" in error_str and attempt < max_retries - 1:
                    logger.warning(f"Rate limited, waiting {retry_delay}s for TPM reset (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    continue
                logger.exception(f"LLM error: model={model}, error={e}")
                self._last_llm_error = last_error
                return None

        if last_error:
            self._last_llm_error = last_error
        return None

    def _extract_status_code(self, error_str: str) -> Optional[str]:
        """Extract HTTP status code from error string."""
        import re
        patterns = [
            r'status_code=(\d{3})',
            r'HTTPStatusError.*?(\d{3})',
            r'"code":\s*(\d{3})',
            r'\b500\b',
            r'\b429\b',
            r'\b400\b',
            r'\b401\b',
            r'\b403\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, error_str)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None

    def _extract_error_body(self, error_str: str) -> Optional[str]:
        """Extract error body from error string."""
        import re
        patterns = [
            r'body:\s*(\[.*\]|\{.*\})',
            r'"message":\s*"([^"]+)"',
            r'error:\s*(\{[^}]+\})',
        ]
        for pattern in patterns:
            match = re.search(pattern, error_str, re.DOTALL)
            if match:
                return match.group(1)[:2000]
        return None

    def _trim_context(self, context: List[Dict]) -> List[Dict]:
        """Trim context to max size."""
        if len(context) > self._max_context:
            context[:] = context[-self._max_context:]
        return context

    @staticmethod
    def clean_response_content(content: str) -> str:
        """
        Clean LLM response content by removing internal tags.

        Strips <thought>...</thought> and <tool_code>...</tool_code> blocks
        that are used internally but should not be shown to the user.
        """
        import re
        # Remove <thought>...</thought> blocks (multiline)
        content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL)
        # Remove <tool_code>...</tool_code> blocks (multiline)
        content = re.sub(r'<tool_code>.*?</tool_code>', '', content, flags=re.DOTALL)
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    @staticmethod
    def strip_internal_tool_fields(tools: List[Dict]) -> List[Dict]:
        """
        Strip internal fields from tool definitions for LLM providers that
        expect clean OpenAI-compatible tool format (Google, Groq).
        
        Removes fields like 'meta' that are used internally but not part
        of the standard OpenAI tool schema.
        """
        if not tools:
            return tools
            
        cleaned_tools = []
        for tool in tools:
            if not isinstance(tool, dict):
                cleaned_tools.append(tool)
                continue
                
            # Create a copy without internal fields
            cleaned_tool = dict(tool)
            
            # Remove 'meta' field at top level (this is what causes Google API error)
            cleaned_tool.pop('meta', None)
                
            # Also clean nested function object if present
            if 'function' in cleaned_tool and isinstance(cleaned_tool['function'], dict):
                func = dict(cleaned_tool['function'])
                # Remove any internal fields from function
                func.pop('meta', None)
                cleaned_tool['function'] = func
                
            cleaned_tools.append(cleaned_tool)
            
        return cleaned_tools

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