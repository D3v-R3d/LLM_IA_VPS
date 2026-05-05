"""
Web Search Service

Search the web for information using Ollama Cloud web search API.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings


logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Service for searching the web.

    Uses Ollama Cloud web search API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize web search service.

        Args:
            api_key: Ollama Cloud API key
        """
        self.api_key = api_key or settings.OLLAMA_API_KEY

    async def search(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search the web.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            Search results with titles, URLs, and snippets

        Example:
            results = await service.search("Python tutorial", num_results=3)
            for r in results["results"]:
                print(f"{r['title']}: {r['url']}")
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
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

    async def search_and_fetch(
        self,
        query: str,
        max_content_length: int = 3000
    ) -> Dict[str, Any]:
        """
        Search web and fetch content from most relevant result.

        Args:
            query: Search query
            max_content_length: Maximum characters to fetch

        Returns:
            Search results plus content from top result
        """
        from app.services.tools.url_fetch import URLFetchService

        search_result = await self.search(query, num_results=1)

        if not search_result.get("success") or not search_result.get("results"):
            return search_result

        first_url = search_result["results"][0].get("url", "")

        if not first_url:
            return {
                "success": True,
                "query": query,
                "results": search_result["results"],
                "fetched_content": "Could not extract URL"
            }

        url_fetch = URLFetchService()
        fetch_result = await url_fetch.fetch(first_url, max_length=max_content_length)

        return {
            "success": True,
            "query": query,
            "results": search_result["results"],
            "fetched_content": fetch_result.get("content", ""),
            "source_url": first_url
        }