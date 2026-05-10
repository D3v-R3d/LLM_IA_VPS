"""
AsyncTool Base Class

Base class for asynchronous tools.
Inherits from BaseTool (which already defines async execute).
Can be used to explicitly mark tools as async.
"""

from app.services.agent_tools.base.base_tool import BaseTool


class AsyncTool(BaseTool):
    """
    Base class for asynchronous tools.
    
    Inherits from BaseTool.
    Tools that are naturally async should inherit this (or BaseTool directly).
    """
    pass
