"""
Vector search tool (Qdrant).
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class QdrantSearchTool(BaseTool):
    """Search Qdrant vector store for similar content."""

    META = {"category": "memory", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "qdrant_search"

    @property
    def description(self) -> str:
        return "Search the Qdrant vector database for semantically similar content. Use this to find relevant stored documents, messages, or knowledge."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "collection": {"type": "string", "description": "Qdrant collection name"},
                "limit": {"type": "integer", "description": "Max number of results (default 5)"}
            },
            "required": ["query", "collection"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.document.vector_storage import VectorStorageService

        query = kwargs.get("query", "")
        collection = kwargs.get("collection", "document")
        limit = kwargs.get("limit", 5)

        if not query:
            return ToolResult(success=False, error="Missing query")
        if not collection:
            return ToolResult(success=False, error="Missing collection")

        try:
            service = VectorStorageService()
            if not service.collection_exists(collection):
                return ToolResult(success=False, error=f"Collection not found: {collection}")

            result = service.scroll_points(collection_name=collection, limit=limit)

            points = result.get("points", [])
            formatted = []
            for p in points:
                payload = p.get("payload", {})
                formatted.append({
                    "id": p.get("id"),
                    "content": payload.get("content", ""),
                    "metadata": payload.get("metadata", {})
                })

            return ToolResult(success=True, data={
                "points": formatted,
                "total": len(formatted)
            })

        except Exception as e:
            return ToolResult(success=False, error=str(e))