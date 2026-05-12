"""
Anthropic Tool Adapter

Converts between canonical tool schema and Anthropic tool format.
"""

from typing import List, Dict, Any
import json

from app.providers.adapters.base_adapter import BaseAdapter


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Claude provider."""

    def to_provider_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert canonical tools to Anthropic tool format.

        Input: list of canonical schemas (from BaseTool.to_canonical())
        Output: list of {"name": ..., "description": ..., "input_schema": ...}
        """
        result = []
        for tool in tools:
            result.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            })
        return result

    def parse_tool_call(self, provider_response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Anthropic response content blocks.

        Expects provider_response to have a "content" list of blocks.
        Each block of type "tool_use" has: id, name, input (dict or string).

        Returns list of dicts: [{"id": "...", "name": "...", "arguments": {...}}]
        """
        tool_calls = []
        # Handle different response shapes
        content = None
        if isinstance(provider_response, dict):
            content = provider_response.get("content")
        elif hasattr(provider_response, "content"):
            content = provider_response.content
        else:
            content = []

        if not isinstance(content, list):
            return tool_calls

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            call_id = block.get("id")
            name = block.get("name")
            input_data = block.get("input")
            # input may be dict or string (if string, try to parse as JSON)
            if isinstance(input_data, str):
                try:
                    arguments = json.loads(input_data)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = input_data if isinstance(input_data, dict) else {}
            if call_id and name:
                tool_calls.append({
                    "id": call_id,
                    "name": name,
                    "arguments": arguments if isinstance(arguments, dict) else {}
                })
        return tool_calls