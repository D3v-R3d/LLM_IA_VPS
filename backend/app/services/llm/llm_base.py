"""
LLM HTTP Client Base

Base HTTP client for LLM API interactions.
"""

import httpx
from typing import Dict, Optional

_client_cache: Dict[str, httpx.AsyncClient] = {}
_cache_lock = None


def _get_cached_client(base_url: str, api_key: Optional[str] = None) -> httpx.AsyncClient:
    """Get or create a cached HTTP client for the given base URL."""
    global _client_cache, _cache_lock
    cache_key = f"{base_url}:{api_key}"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = httpx.AsyncClient(timeout=180.0)
    return _client_cache[cache_key]


class LLMBaseClient:
    """
    Base HTTP client for LLM APIs.

    Handles common HTTP operations and authentication.
    Uses cached HTTP clients for connection reuse.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize base client.

        Args:
            base_url: API base URL
            api_key: Optional API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key
        self.client = _get_cached_client(base_url, api_key)

    def _get_headers(self) -> Dict[str, str]:
        """
        Build request headers with optional auth.

        Returns:
            Headers dictionary
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def close(self):
        """Close HTTP client (no-op, clients are cached)."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass