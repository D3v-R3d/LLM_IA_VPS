"""
Base Tool Interface

All tools inherit from BaseTool and implement the execute method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = None

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
    - parameters: dict describing expected parameters
    - execute(): the actual tool logic
    """

    def __init__(self):
        self._last_result: Optional[ToolResult] = None

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
    def parameters(self) -> Dict[str, Any]:
        """
        JSON schema for tool parameters.
        Override in subclass for custom parameters.
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class SyncTool(BaseTool):
    """
    Base class for synchronous tools.
    Converts sync execute to async for uniform interface.
    """

    @abstractmethod
    def _execute_sync(self, **kwargs) -> ToolResult:
        """Synchronous implementation."""
        pass

    async def execute(self, **kwargs) -> ToolResult:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(**kwargs)
        )