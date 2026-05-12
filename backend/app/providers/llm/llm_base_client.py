"""
LLM Base Client

Production-ready async HTTP layer for LLM providers.
Supports connection pooling, reuse, and clean architecture.
"""

from typing import Dict, Optional

from app.providers.llm.http_client_pool import HttpClientPool


class LLMBaseClient:
    """
    Base client for all LLM providers.

    Responsibilities:
    - HTTP abstraction
    - Provider communication
    - Connection reuse via pool

    NOT responsible for:
    - prompts
    - orchestration
    - tool execution
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[HttpClientPool] = None

    async def _get_client(self) -> HttpClientPool:
        """
        Lazy-load pooled HTTP client.
        """
        if not self._client:
            self._client = await HttpClientPool.get_client(
                self.base_url,
                self.api_key
            )
        return self._client

    # ─────────────────────────────────────────────
    # REQUEST LAYER
    # ─────────────────────────────────────────────

    async def post(self, path: str, payload: dict) -> dict:
        """
        Generic POST request to LLM provider.
        """

        client = await self._get_client()

        url = f"{self.base_url}{path}"

        response = await client.post(
            url,
            json=payload
        )

        response.raise_for_status()
        return response.json()

    async def get(self, path: str) -> dict:
        """
        Generic GET request.
        """
        client = await self._get_client()

        url = f"{self.base_url}{path}"

        response = await client.get(url)
        response.raise_for_status()
        return response.json()

    # ─────────────────────────────────────────────
    # HEADERS (optional override hook)
    # ─────────────────────────────────────────────

    def _get_headers(self) -> Dict[str, str]:
        """
        Default headers (only used if provider overrides HTTP logic).
        """
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    # ─────────────────────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────────────────────

    async def close(self):
        """
        No-op because lifecycle is managed by pool.
        """
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass