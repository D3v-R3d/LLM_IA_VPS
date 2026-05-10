"""
Base Tool Interface (Refactored)

All tools inherit from BaseTool and implement the execute method.
Stateless, provider-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.agent_tools.base.schemas import CANONICAL_TOOL_SCHEMA, validate_canonical_tool


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Each tool must implement:
    - name: unique tool identifier
    - description: what the tool does
    - parameters: dict describing expected parameters (JSON Schema)
    - execute(): the actual tool logic

    Tool metadata (override in subclass via META class attribute):
    - category: tool group for routing
    - max_calls_per_run: 0 = unlimited
    - parallel_safe: can run in parallel with other tools
    """

    META = {
        "category": "util",
        "max_calls_per_run": 0,
        "parallel_safe": True,
    }

    def __init__(self):
        # No state kept here (stateless tools)
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    def category(self) -> str:
        """Tool group for routing (file, web, system, memory, etc.)."""
        return self.META.get("category", "util")

    @property
    def max_calls_per_run(self) -> int:
        """Max calls per agent run. 0 = unlimited."""
        return self.META.get("max_calls_per_run", 0)

    @property
    def parallel_safe(self) -> bool:
        """Can this tool run in parallel with others."""
        return self.META.get("parallel_safe", True)

    @property
    def parameters(self) -> Dict[str, Any]:
        """
        JSON Schema for tool parameters.
        Override in subclass for custom parameters.
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def to_canonical(self) -> Dict[str, Any]:
        """
        Return tool definition in canonical schema.
        This is the single source of truth for tool metadata.
        """
        canonical = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "meta": {
                "category": self.category,
                "max_calls_per_run": self.max_calls_per_run,
                "parallel_safe": self.parallel_safe,
            }
        }
        # Optionally validate
        if not validate_canonical_tool(canonical):
            # Log warning but still return
            import logging
            logging.getLogger(__name__).warning(f"Tool {self.name} does not match canonical schema")
        return canonical

    def to_definition(self) -> Dict[str, Any]:
        """Tool definition for LLM function calling (OpenAI-style, kept for compatibility)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with success status and data/error
        """
        pass

    def validate_args(self, **kwargs) -> Optional[str]:
        """
        Validate arguments against parameters schema.
        Returns error string if invalid, None if valid.
        Override for custom validation.
        """
        # Basic validation: check required parameters
        required = self.parameters.get("required", [])
        for req in required:
            if req not in kwargs:
                return f"Missing required parameter: {req}"
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
