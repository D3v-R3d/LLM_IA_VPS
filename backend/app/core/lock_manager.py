"""
Lock Manager Service

Replaces global _conversation_locks dict with a proper service class.
Thread-safe and async-safe lock management per conversation.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class LockWithTimestamp(asyncio.Lock):
    """Lock with timestamp tracking for cleanup."""
    def __init__(self):
        super().__init__()
        self._last_used = time.time()
        self._key: str = ""

    def touch(self):
        """Update last used timestamp."""
        self._last_used = time.time()


class LockManager:
    """
    Service for managing per-conversation locks.

    Replaces global _conversation_locks dict.
    Provides automatic cleanup of stale locks.
    """

    def __init__(
        self,
        cleanup_interval: int = 300,
        lock_timeout: int = 60
    ):
        self._locks: dict[str, asyncio.Lock] = {}
        self._cleanup_interval = cleanup_interval
        self._lock_timeout = lock_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def get(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a given key."""
        if key not in self._locks:
            lock = LockWithTimestamp()
            lock._key = key
            self._locks[key] = lock
        else:
            lock = self._locks[key]
            if hasattr(lock, 'touch'):
                lock.touch()
        return self._locks[key]

    async def acquire(self, key: str) -> asyncio.Lock:
        """Get lock for a key (does NOT acquire - caller uses async with)."""
        lock = await self.get(key)
        return lock

    async def release(self, key: str) -> None:
        """Release lock for a key if held."""
        if key in self._locks:
            lock = self._locks[key]
            if lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

    async def is_locked(self, key: str) -> bool:
        """Check if a key is currently locked."""
        if key in self._locks:
            return self._locks[key].locked()
        return False

    async def start_cleanup_task(self) -> None:
        """Start background cleanup task for stale locks."""
        if self._running:
            return

        self._running = True

        async def _cleanup_loop():
            while self._running:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self._cleanup_stale_locks()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Lock cleanup error: {e}")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info("LockManager cleanup task started")

    async def stop(self) -> None:
        """Stop cleanup task and release all locks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        for key in list(self._locks.keys()):
            if self._locks[key].locked():
                try:
                    self._locks[key].release()
                except RuntimeError:
                    pass
            del self._locks[key]

        logger.info("LockManager stopped")

    async def _cleanup_stale_locks(self) -> int:
        """Remove stale locks. Returns number of locks removed."""
        now = time.time()
        to_remove = []

        for key, lock in self._locks.items():
            if hasattr(lock, '_last_used'):
                age = now - lock._last_used
                if age > self._cleanup_interval and not lock.locked():
                    to_remove.append(key)

        for key in to_remove:
            del self._locks[key]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} stale locks")

        return len(to_remove)

    @property
    def lock_count(self) -> int:
        """Number of active locks."""
        return len(self._locks)


_lock_manager: Optional[LockManager] = None


def get_lock_manager() -> LockManager:
    """Get or create global LockManager instance."""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = LockManager()
    return _lock_manager