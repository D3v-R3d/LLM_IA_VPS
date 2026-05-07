"""
Web Tools - WebFetch, WebSearch, APIFetch

Tools for web operations using services from app.services.agent_tools.tools.
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch content from a URL. Returns HTML/text content."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_length": {"type": "integer", "description": "Max characters to return (default 4000)"}
            },
            "required": ["url"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.agent_tools.tools.url_fetch import URLFetchService
        url = kwargs.get("url")
        max_length = kwargs.get("max_length", 4000)

        try:
            service = URLFetchService()
            result = await service.fetch(url, max_length)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WebSearchTool(BaseTool):
    """Search the web."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information. Returns titles, URLs and snippets."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (default 5)"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.agent_tools.tools.web_search import WebSearchService
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 5)

        try:
            service = WebSearchService()
            result = await service.search(query, num_results)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class APIFetchTool(BaseTool):
    """Call an external API."""

    @property
    def name(self) -> str:
        return "api_fetch"

    @property
    def description(self) -> str:
        return "Call an external API endpoint."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                "headers": {"type": "object", "description": "HTTP headers"},
                "body": {"type": "object", "description": "Request body"}
            },
            "required": ["url"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.agent_tools.tools.api_caller import APICallerService
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        body = kwargs.get("body")

        try:
            service = APICallerService()
            result = await service.call(url, method, headers, body)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))