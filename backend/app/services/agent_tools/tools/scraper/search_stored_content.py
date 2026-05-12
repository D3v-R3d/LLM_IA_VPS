"""
Search stored content tool.
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class SearchStoredContentTool(BaseTool):
    """
    Search stored web content using semantic search.
    """

    META = {"category": "search", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "search_stored_content"

    @property
    def description(self) -> str:
        return """Search through previously stored web content using semantic similarity.
Use this when user wants to find information they previously scraped and stored.

Input: search query and optional parameters (collection_name, limit, score_threshold)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "collection_name": {
                    "type": "string",
                    "description": "VectorDB collection to search",
                    "default": "web_content"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5
                },
                "score_threshold": {
                    "type": "number",
                    "description": "Minimum relevance score (0-1)",
                    "default": 0.5
                }
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.document import DataPipelineService

        query = kwargs.get("query", "")
        collection_name = kwargs.get("collection_name", "web_content")
        limit = kwargs.get("limit", 5)
        score_threshold = kwargs.get("score_threshold", 0.5)

        if not query:
            return ToolResult(success=False, error="No query provided")

        try:
            pipeline = DataPipelineService()
            result = await pipeline.search_stored(
                query=query,
                collection_name=collection_name,
                limit=limit,
                score_threshold=score_threshold
            )

            if not result.get("success"):
                return ToolResult(success=False, error=result.get("error", "Search failed"))

            return ToolResult(success=True, data=result.get("results"))

        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {str(e)}")