"""
LLM HTTP Client Base

Base HTTP client for LLM API interactions.
"""

import httpx
from typing import Dict, Optional


class LLMBaseClient:
    """
    Base HTTP client for LLM APIs.

    Handles common HTTP operations and authentication.
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
        self.client = httpx.AsyncClient(timeout=15.0)

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
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()