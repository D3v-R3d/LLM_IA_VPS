"""
HTTP Client Pool for LLM Providers

Global async HTTP client pool.
Supports connection pooling, reuse, and clean architecture.
"""

from typing import Dict, Optional
import httpx
import asyncio


class HttpClientPool:
    """
    Global async HTTP client pool.

    - Reuses connections
    - Avoids socket exhaustion
    - Safe for async concurrent usage
    """

    _clients: Dict[str, httpx.AsyncClient] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def get_client(
        cls,
        base_url: str,
        api_key: Optional[str] = None
    ) -> httpx.AsyncClient:

        cache_key = f"{base_url}:{api_key or 'no-key'}"

        async with cls._lock:
            if cache_key not in cls._clients:
                cls._clients[cache_key] = httpx.AsyncClient(
                    timeout=httpx.Timeout(300.0),
                    limits=httpx.Limits(
                        max_connections=50,
                        max_keepalive_connections=10
                    ),
                    headers={
                        "Content-Type": "application/json",
                        **(
                            {"Authorization": f"Bearer {api_key}"}
                            if api_key else {}
                        )
                    }
                )

            return cls._clients[cache_key]

    @classmethod
    async def close_all(cls):
        """Graceful shutdown of all HTTP clients."""
        async with cls._lock:
            for client in cls._clients.values():
                await client.aclose()
            cls._clients.clear()