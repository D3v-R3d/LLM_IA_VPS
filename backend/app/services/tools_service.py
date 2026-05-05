"""
Tools Service Module

Provides tools for LLM to interact with external services:
- Web search (DuckDuckGo)
- URL fetching (HTTP get content)
- API calls (custom HTTP requests)

Tools can be used by Ollama Cloud models that support function calling.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlencode
import httpx

logger = logging.getLogger(__name__)


class ToolsService:
    """
    Service providing tools for LLM external interactions.
    """

    def __init__(self):
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Quick web search for facts. Returns titles, URLs and short snippets (200-500 chars). Use for simple factual queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_url",
                    "description": "Fetch content from a URL. Use when you need to read a specific webpage.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to fetch"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Max characters to return (default 4000)",
                                "default": 4000
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "call_api",
                    "description": "Call an external API endpoint. Use for structured data or programmatic access.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "API endpoint URL"
                            },
                            "method": {
                                "type": "string",
                                "description": "HTTP method (GET, POST, etc)",
                                "default": "GET"
                            },
                            "headers": {
                                "type": "object",
                                "description": "HTTP headers as key-value pairs"
                            },
                            "body": {
                                "type": "object",
                                "description": "Request body for POST"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_and_fetch",
                    "description": "Search web AND get full content from most relevant page. Use when you need detailed, current information (articles, news, specific facts). This gives you the complete page content, not just snippets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools definition for LLM."""
        return self.tools

    async def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Search the web using Ollama Cloud API.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            Dict with search results
        """
        try:
            from app.core.config import settings

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
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

    async def fetch_url(self, url: str, max_length: int = 4000) -> Dict[str, Any]:
        """
        Fetch content from a URL.

        Args:
            url: URL to fetch
            max_length: Maximum characters to return

        Returns:
            Dict with fetched content
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; TowerBot/1.0)"
                }
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    content = response.text[:max_length]
                    return {
                        "success": True,
                        "url": url,
                        "content": content,
                        "truncated": len(response.text) > max_length
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Fetch failed: {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"URL fetch error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def call_api(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call an external API.

        Args:
            url: API endpoint URL
            method: HTTP method
            headers: Optional headers
            body: Optional request body

        Returns:
            Dict with API response
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_headers = headers or {}
                request_headers["User-Agent"] = "TowerBot/1.0"

                request_kwargs = {
                    "url": url,
                    "headers": request_headers
                }

                if method.upper() in ["POST", "PUT", "PATCH"] and body:
                    request_kwargs["json"] = body

                response = await client.request(method, **request_kwargs)

                return {
                    "success": True,
                    "url": url,
                    "status": response.status_code,
                    "body": response.text[:4000]
                }

        except Exception as e:
            logger.error(f"API call error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def search_and_fetch(self, query: str) -> Dict[str, Any]:
        """
        Search the web and fetch content from most relevant result.

        Args:
            query: Search query

        Returns:
            Dict with search results AND fetched content from first URL
        """
        search_result = await self.search_web(query, num_results=1)

        if not search_result.get("success") or not search_result.get("results"):
            return search_result

        first_url = search_result["results"][0].get("url", "")

        if not first_url:
            return {
                "success": True,
                "query": query,
                "results": search_result["results"],
                "fetched_content": "Could not extract URL from search results"
            }

        import re
        from html import unescape

        def strip_html(html_text: str) -> str:
            """Remove HTML tags and clean text."""
            text = re.sub(r'<[^>]+>', ' ', html_text)
            text = unescape(text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        fetch_result = await self.fetch_url(first_url, max_length=3000)

        raw_content = fetch_result.get('content', '')
        clean_content = strip_html(raw_content)

        content_for_llm = f"""
Search query: {query}

Top result: {search_result['results'][0].get('title', '')}
URL: {first_url}

Content from page:
{clean_content}
"""

        return {
            "success": True,
            "query": query,
            "results": search_result["results"],
            "fetched_content": content_for_llm,
            "source_url": first_url
        }

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with arguments.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name == "search_web":
            return await self.search_web(
                query=arguments.get("query", ""),
                num_results=arguments.get("num_results", 5)
            )
        elif tool_name == "fetch_url":
            return await self.fetch_url(
                url=arguments.get("url", ""),
                max_length=arguments.get("max_length", 4000)
            )
        elif tool_name == "call_api":
            return await self.call_api(
                url=arguments.get("url", ""),
                method=arguments.get("method", "GET"),
                headers=arguments.get("headers"),
                body=arguments.get("body")
            )
        elif tool_name == "search_and_fetch":
            return await self.search_and_fetch(
                query=arguments.get("query", "")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

    def format_tools_for_llm(self) -> str:
        """Format tools as a description string for LLM."""
        tools_desc = []
        for tool in self.tools:
            func = tool["function"]
            tools_desc.append(
                f"- {func['name']}: {func['description']}"
            )
        return "\n".join(tools_desc)