"""
Web fetch tool.
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    META = {"category": "web", "max_calls_per_run": 0, "parallel_safe": True}

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

        if not url:
            return ToolResult(success=False, error="Missing url")

        try:
            service = URLFetchService()
            result = await service.fetch(url, max_length)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))