"""
Base Adapter

Abstract base class for provider-specific tool adapters.
Converts between canonical tool schema and provider-specific formats.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseAdapter(ABC):
    """Abstract base for provider tool adapters."""

    @abstractmethod
    def to_provider_format(self, tools: List[Dict[str, Any]]) -> Any:
        """
        Convert canonical tool schemas to provider-specific format.

        Args:
            tools: List of canonical tool schemas (from BaseTool.to_canonical())

        Returns:
            Provider-specific representation of tools.
        """
        pass

    @abstractmethod
    def parse_tool_call(self, provider_response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from provider response.

        Args:
            provider_response: Raw response from provider's chat_with_tools

        Returns:
            List of dicts with keys: id, name, arguments (dict)
            Example: [{"id": "call_abc", "name": "read_file", "arguments": {"path": "/tmp/file.txt"}}]
        """
        pass