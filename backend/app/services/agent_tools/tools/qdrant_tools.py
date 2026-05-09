"""
Qdrant Tools - Search and retrieve stored embeddings.

Tools for searching the vector database for semantic content.
"""

from typing import Optional, Dict, Any

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


class QdrantSearchTool(BaseTool):
    """Search Qdrant vector store for similar content."""

    META = {"category": "search", "max_calls_per_run": 0, "parallel_safe": True}

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
        from app.services.llm.embedding import EmbeddingService

        query = kwargs.get("query", "")
        collection = kwargs.get("collection", "documents")
        limit = kwargs.get("limit", 5)

        try:
            service = VectorStorageService()
            if not service.collection_exists(collection):
                return ToolResult(success=False, error=f"Collection not found: {collection}")

            embed_service = EmbeddingService()
            embedding = await embed_service.embed_single(query)
            if not embedding:
                return ToolResult(success=False, error="Failed to generate embedding for query")

            results = service.search(
                collection_name=collection,
                query_vector=embedding,
                limit=limit
            )

            if not results:
                return ToolResult(success=True, data={"results": [], "message": "No results found"})

            formatted = []
            for r in results:
                payload = r.get("payload", {})
                formatted.append({
                    "score": r.get("score", 0),
                    "content": payload.get("content", ""),
                    "document_id": payload.get("document_id"),
                    "metadata": payload.get("metadata", {})
                })

            return ToolResult(success=True, data={"results": formatted})

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class QdrantScrollTool(BaseTool):
    """Scroll through all stored content in a Qdrant collection."""

    META = {"category": "search", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "qdrant_scroll"

    @property
    def description(self) -> str:
        return "Scroll through all stored content in a Qdrant collection to list documents or messages."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection": {"type": "string", "description": "Qdrant collection name"},
                "limit": {"type": "integer", "description": "Max items to return (default 20)"}
            },
            "required": ["collection"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.document.vector_storage import VectorStorageService

        collection = kwargs.get("collection", "documents")
        limit = kwargs.get("limit", 20)

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