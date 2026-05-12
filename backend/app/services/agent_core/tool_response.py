"""
Tool Response

Standardized envelope for all tool outputs.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.agent_core.tool_metadata import ToolMetadata


@dataclass
class ToolResponse:
    """Standardized tool output envelope."""
    success: bool
    tool: str
    summary: str
    data: Any = None
    error: Optional[str] = None
    metadata: ToolMetadata = field(default_factory=ToolMetadata)

    def to_llm_message(self) -> dict:
        return {
            "role": "tool",
            "content": self.summary,
        }

    def to_log_dict(self) -> dict:
        return {
            "tool": self.tool,
            "success": self.success,
            "summary_len": len(self.summary),
            "has_data": self.data is not None,
            "error": self.error,
            "duration_ms": self.metadata.duration_ms,
        }