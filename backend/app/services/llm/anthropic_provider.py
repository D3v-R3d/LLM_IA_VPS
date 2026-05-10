"""
Anthropic Claude Provider

LLM provider implementation for Anthropic Claude API.
Uses the official Anthropic SDK.
Tool formatting delegated to AnthropicAdapter.
"""

import json
import logging
from typing import List, Dict, Any, Optional

import anthropic
from app.services.llm.llm_provider import LLMProvider
from app.core.config import settings
from app.services.agent_tools.providers.adapters.anthropic_adapter import AnthropicAdapter

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude API provider.

    Models: claude-sonnet-4-20250514, claude-3-5-sonnet-20241022, etc.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            timeout=180.0
        )
        self._adapter = AnthropicAdapter()

    @property
    def name(self) -> str:
        return "anthropic"

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert OpenAI-style messages to Anthropic format.

        Returns: (system, clean_messages)
        """
        system = None
        clean_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system = str(content) if content else None
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # Convert tool_calls to Anthropic tool_use blocks
                    blocks = []
                    if content:
                        blocks.append({"type": "text", "text": str(content)})
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        args = func.get("arguments", {})
                        # Handle string arguments
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except:
                                args = {}
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": args
                        })
                    clean_messages.append({"role": "assistant", "content": blocks})
                else:
                    clean_messages.append({"role": "assistant", "content": str(content) if content else ""})
            elif role == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    clean_messages.append({"role": "user", "content": content})
                else:
                    clean_messages.append({"role": "user", "content": str(content) if content else ""})
            elif role == "tool":
                # Convert OpenAI tool result to Anthropic format
                tool_call_id = msg.get("tool_call_id", "")
                content = msg.get("content", "")
                clean_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": str(content) if content else ""
                    }]
                })
            else:
                clean_messages.append({"role": role, "content": str(content) if content else ""})

        return system, clean_messages

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion."""
        try:
            system, clean_messages = self._convert_messages(messages)

            response = await self._client.messages.create(
                model=model,
                system=system,
                messages=clean_messages,
                max_tokens=options.get("max_tokens", 1024) if options else 1024,
                temperature=options.get("temperature", 0.7) if options else 0.7,
            )

            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                    break

            return {
                "model": response.model,
                "message": {
                    "role": "assistant",
                    "content": text_content
                },
                "done": True
            }
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            raise

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion with tool calling."""
        try:
            system, clean_messages = self._convert_messages(messages)
            # Convert from OpenAI format to canonical format for Anthropic adapter
            canonical_tools = []
            for tool in tools:
                if "function" in tool:
                    canonical_tools.append(tool["function"])
                else:
                    canonical_tools.append(tool)
            tool_schema = self._adapter.to_provider_format(canonical_tools)

            response = await self._client.messages.create(
                model=model,
                system=system,
                messages=clean_messages,
                tools=tool_schema,
                max_tokens=options.get("max_tokens", 1024) if options else 1024,
                temperature=options.get("temperature", 0.7) if options else 0.7,
            )

            tool_calls = []
            text_content = ""

            for block in response.content:
                if block.type == "tool_use":
                    args = block.input if isinstance(block.input, dict) else {}
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": args
                        }
                    })
                elif block.type == "text":
                    text_content = block.text

            return {
                "model": response.model,
                "message": {
                    "role": "assistant",
                    "content": text_content,
                    "tool_calls": tool_calls
                },
                "done": True
            }
        except Exception as e:
            logger.error(f"Anthropic chat_with_tools error: {e}")
            raise

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        return [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
        ]

    async def health_check(self) -> bool:
        """Check if Anthropic API is reachable."""
        try:
            await self._client.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False

    async def close(self):
        """Close the client."""
        pass