"""
API call tool.
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class APIFetchTool(BaseTool):
    """Call an external API."""

    META = {"category": "web", "max_calls_per_run": 0, "parallel_safe": True}

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

        if not url:
            return ToolResult(success=False, error="Missing url")

        try:
            service = APICallerService()
            result = await service.call(url, method, headers, body)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))