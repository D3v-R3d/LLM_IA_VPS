"""
OpenAI Tool Adapter

Converts between canonical tool schema and OpenAI function-calling format.
"""

from typing import List, Dict, Any
import json

from app.services.agent_tools.providers.adapters.base_adapter import BaseAdapter


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI-compatible providers (OpenAI, Groq, Ollama)."""

    def to_provider_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert canonical tools to OpenAI function-calling format.

        Input: list of canonical schemas (from BaseTool.to_canonical())
        Output: list of {"type":"function","function":{"name":..., "description":..., "parameters":...}}
        """
        result = []
        for tool in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
            })
        return result

    def parse_tool_call(self, provider_response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from OpenAI-style response.

        Expects provider_response to have a "message" field with "tool_calls" list.
        Each tool_call: {"id": "...", "type": "function", "function": {"name": "...", "arguments": "json-string"}}

        Returns list of dicts: [{"id": "...", "name": "...", "arguments": {...}}]
        """
        tool_calls = []
        # Handle different response shapes
        if isinstance(provider_response, dict):
            # Common shape: {"message": {"tool_calls": [...]}} or directly {"tool_calls": [...]}
            message = provider_response.get("message", provider_response)
            raw_calls = message.get("tool_calls", [])
        elif hasattr(provider_response, "message"):  # object with attribute
            message = provider_response.message
            raw_calls = getattr(message, "tool_calls", [])
        else:
            raw_calls = []

        for call in raw_calls:
            if not isinstance(call, dict):
                continue
            call_id = call.get("id")
            call_type = call.get("type")
            if call_type != "function":
                continue
            function_info = call.get("function", {})
            if not isinstance(function_info, dict):
                continue
            name = function_info.get("name")
            args_str = function_info.get("arguments", "{}")
            try:
                arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                arguments = {}
            if call_id and name:
                tool_calls.append({
                    "id": call_id,
                    "name": name,
                    "arguments": arguments if isinstance(arguments, dict) else {}
                })
        return tool_calls