"""
Web tools.
"""

from app.services.agent_tools.tools.web.web_fetch import WebFetchTool
from app.services.agent_tools.tools.web.web_search import WebSearchTool
from app.services.agent_tools.tools.web.api_call import APIFetchTool

__all__ = [
    "WebFetchTool",
    "WebSearchTool",
    "APIFetchTool",
]