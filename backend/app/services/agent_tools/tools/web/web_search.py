"""
Web search tool.
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


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

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.agent_tools.tools.web_search import WebSearchService
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 5)

        if not query:
            return ToolResult(success=False, error="Missing query")

        try:
            service = WebSearchService()
            result = await service.search(query, num_results)
            return ToolResult(success=result.get("success", False), data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))