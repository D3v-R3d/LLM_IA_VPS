"""
Rate Limiter Service

Replaces global _rate_limit_per_chat dict with a proper service class.
Provides per-key rate limiting with automatic cleanup.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Service for per-key rate limiting.

    Replaces global _rate_limit_per_chat dict.
    Tracks request timestamps per key and enforces rate limits.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 5
    ):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = {}

    async def allow(self, key: str) -> bool:
        """
        Check if a request from key is allowed under rate limit.

        Returns True if allowed, False if rate limited.
        """
        now = time.time()
        self._requests.setdefault(key, [])

        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < self._window
        ]

        if len(self._requests[key]) >= self._max_requests:
            logger.warning(f"Rate limit exceeded for key={key}")
            return False

        self._requests[key].append(now)
        return True

    async def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key in current window."""
        now = time.time()
        if key not in self._requests:
            return self._max_requests

        active = [
            t for t in self._requests[key]
            if now - t < self._window
        ]

        return max(0, self._max_requests - len(active))

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._requests:
            self._requests[key] = []

    async def cleanup(self) -> int:
        """Remove old entries. Returns number of keys cleaned."""
        now = time.time()
        to_remove = []

        for key, timestamps in self._requests.items():
            active = [t for t in timestamps if now - t < self._window]
            if not active:
                to_remove.append(key)
            else:
                self._requests[key] = active

        for key in to_remove:
            del self._requests[key]

        return len(to_remove)

    @property
    def key_count(self) -> int:
        """Number of keys being tracked."""
        return len(self._requests)


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter