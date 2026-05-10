"""
SyncTool Base Class

Base class for synchronous tools.
Converts sync execute to async for uniform interface.
"""

import asyncio
from abc import abstractmethod
from typing import Dict, Any, Optional
from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class SyncTool(BaseTool):
    """
    Base class for synchronous tools.
    
    Implement _execute_sync() instead of execute().
    The execute() method will run _execute_sync in a thread executor.
    """
    
    @abstractmethod
    def _execute_sync(self, **kwargs) -> ToolResult:
        """Synchronous implementation of the tool logic."""
        pass
    
    async def execute(self, **kwargs) -> ToolResult:
        """Run synchronous tool in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._execute_sync(**kwargs)
        )
