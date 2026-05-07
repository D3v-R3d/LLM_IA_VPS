"""
URL Fetch Service

Fetches content from URLs.
"""

import httpx
import re
import logging
from html import unescape
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class URLFetchService:
    """
    Service for fetching content from URLs.

    Extracts clean text from web pages.
    """

    def __init__(self, user_agent: str = "Mozilla/5.0 (compatible; TowerBot/1.0)"):
        """
        Initialize URL fetch service.

        Args:
            user_agent: User agent string for requests
        """
        self.user_agent = user_agent

    async def fetch(
        self,
        url: str,
        max_length: int = 4000
    ) -> Dict[str, Any]:
        """
        Fetch content from URL.

        Args:
            url: URL to fetch
            max_length: Maximum characters to return

        Returns:
            Fetched content and metadata

        Example:
            result = await service.fetch("https://news.example.com")
            print(result["content"])
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": self.user_agent}
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    content = response.text[:max_length]
                    return {
                        "success": True,
                        "url": url,
                        "content": content,
                        "truncated": len(response.text) > max_length,
                        "content_type": response.headers.get("content-type", "")
                    }
                else:
                    return {
                        "success": False,
                        "url": url,
                        "error": f"Fetch failed: {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"URL fetch error: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

    async def fetch_and_clean(
        self,
        url: str,
        max_length: int = 4000
    ) -> Dict[str, Any]:
        """
        Fetch URL and extract clean text.

        Args:
            url: URL to fetch
            max_length: Maximum characters

        Returns:
            Cleaned text content
        """
        result = await self.fetch(url, max_length)

        if result.get("success"):
            result["content"] = self._clean_html(result.get("content", ""))

        return result

    def _clean_html(self, html_text: str) -> str:
        """
        Remove HTML tags and clean text.

        Args:
            html_text: Raw HTML content

        Returns:
            Clean text
        """
        text = re.sub(r'<[^>]+>', ' ', html_text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()