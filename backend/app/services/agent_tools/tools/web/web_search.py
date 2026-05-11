"""
Web search tool.
"""

import httpx
import logging
from typing import Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.core.config import settings
import re
from html import unescape

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web."""

    META = {"category": "web", "max_calls_per_run": 3, "parallel_safe": True}

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

    async def _search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Execute web search via Ollama Cloud API."""
        api_key = settings.OLLAMA_API_KEY
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                response = await client.post(
                    "https://ollama.com/api/web_search",
                    headers=headers,
                    json={"query": query}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])[:num_results]
                    return {
                        "success": True,
                        "query": query,
                        "results": [
                            {
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("content", "")[:500]
                            }
                            for r in results
                        ]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Search failed: {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _fetch_url(self, url: str, max_length: int = 3000) -> str:
        """Fetch and clean content from URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; TowerBot/1.0)"}
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    text = response.text[:max_length]
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = unescape(text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text
                return ""
        except Exception:
            return ""

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 5)

        if not query:
            return ToolResult(success=False, error="Missing query")

        result = await self._search(query, num_results)
        return ToolResult(success=result.get("success", False), data=result)