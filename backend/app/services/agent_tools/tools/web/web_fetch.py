"""
Web fetch tool.
"""

import re
import logging
from html import unescape
from typing import Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


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
        url = kwargs.get("url")
        max_length = kwargs.get("max_length", 4000)

        if not url:
            return ToolResult(success=False, error="Missing url")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; TowerBot/1.0)"}
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    content = response.text[:max_length]
                    # Clean HTML
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = unescape(content)
                    content = re.sub(r'\s+', ' ', content).strip()

                    return ToolResult(
                        success=True,
                        data={
                            "url": url,
                            "content": content,
                            "truncated": len(response.text) > max_length,
                            "content_type": response.headers.get("content-type", "")
                        }
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"Fetch failed: {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"URL fetch error: {e}")
            return ToolResult(success=False, error=str(e))