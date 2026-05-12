"""
API call tool.
"""

import httpx
import logging
from typing import Optional, Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class APIFetchTool(BaseTool):
    """Call an external API."""

    META = {"category": "web", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "api_call"

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
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        body = kwargs.get("body")
        timeout = kwargs.get("timeout", 30.0)

        if not url:
            return ToolResult(success=False, error="Missing url")

        try:
            request_headers = headers or {}
            request_headers["User-Agent"] = "TowerBot/1.0"

            async with httpx.AsyncClient(timeout=timeout) as client:
                request_kwargs = {
                    "url": url,
                    "headers": request_headers
                }

                if method.upper() in ["POST", "PUT", "PATCH"] and body:
                    request_kwargs["json"] = body

                response = await client.request(method, **request_kwargs)

                return ToolResult(
                    success=True,
                    data={
                        "url": url,
                        "method": method,
                        "status": response.status_code,
                        "body": response.text[:4000],
                        "headers": dict(response.headers)
                    }
                )

        except Exception as e:
            logger.error(f"API call error: {e}")
            return ToolResult(success=False, error=str(e))