"""
Scraper tools.
"""

from typing import Optional
import asyncio

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult


class ScrapeAndStoreTool(BaseTool):
    """
    Tool that scrapes web content, cleans it, chunks it,
    creates embeddings, and stores in vector database.
    """

    META = {"category": "web", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "scrape_and_store"

    @property
    def description(self) -> str:
        return """Scrape web content from URLs, clean it, chunk it, create embeddings, and store in vector database.
Use this when user wants to:
- Save content from URLs for later retrieval
- Build a knowledge base from web sources
- Store research material for semantic search

Input: JSON array of URLs and optional parameters (collection_name, user_id)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of URLs to scrape"
                },
                "collection_name": {
                    "type": "string",
                    "description": "VectorDB collection name for storage",
                    "default": "web_content"
                },
                "user_id": {
                    "type": "string",
                    "description": "User ID for tracking ownership"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Max characters per URL content",
                    "default": 10000
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, scrape and chunk but don't store embeddings",
                    "default": False
                }
            },
            "required": ["urls"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        from app.services.document import DataPipelineService

        urls = kwargs.get("urls", [])
        collection_name = kwargs.get("collection_name", "web_content")
        user_id = kwargs.get("user_id")
        max_length = kwargs.get("max_length", 10000)
        dry_run = kwargs.get("dry_run", False)

        if not urls:
            return ToolResult(success=False, error="No URLs provided")

        if not isinstance(urls, list):
            return ToolResult(success=False, error="urls must be an array")

        if len(urls) > 20:
            return ToolResult(success=False, error="Maximum 20 URLs per request")

        try:
            pipeline = DataPipelineService()
            result = await pipeline.scrape_and_store(
                urls=urls,
                collection_name=collection_name,
                user_id=user_id,
                max_length=max_length,
                store_vectors=not dry_run
            )

            if result.get("failed", 0) > 0 and result.get("successful", 0) == 0:
                return ToolResult(
                    success=False,
                    error=f"All URLs failed. Errors: {[r.get('error') for r in result.get('results', [])]}"
                )

            return ToolResult(
                success=True,
                data=result
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Pipeline failed: {str(e)}")


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