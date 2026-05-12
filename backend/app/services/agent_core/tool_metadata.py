"""
Tool Metadata

Duration and metadata for tool execution responses.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolMetadata:
    """Metadata for tool execution."""
    duration_ms: Optional[int] = None
    tool_name: Optional[str] = None