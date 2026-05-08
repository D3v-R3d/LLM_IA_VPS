"""
Handler Router for Telegram Updates

Dispatches updates to appropriate handlers based on can_handle() method.
Handles registration and ordering of handlers.
"""

import logging
from typing import List, Optional

from app.services.telegram.handlers.base import BaseHandler, TelegramUpdate, HandlerContext

logger = logging.getLogger(__name__)


class HandlerRouter:
    """
    Routes Telegram updates to appropriate handlers.

    Handlers are tried in registration order until one returns True for can_handle().
    """

    def __init__(self):
        self._handlers: List[BaseHandler] = []

    def register(self, handler: BaseHandler) -> None:
        """Register a handler. Will be tried in order."""
        self._handlers.append(handler)

    def unregister(self, handler: BaseHandler) -> None:
        """Remove a handler from the router."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def route(self, update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
        """
        Route an update to the first handler that can handle it.

        Returns:
            Response text from handler, or None
        """
        for handler in self._handlers:
            try:
                if await handler.can_handle(update):
                    logger.info(f"Routing to {handler.__class__.__name__}")
                    return await handler.handle(update, context)
            except Exception as e:
                logger.exception(f"Handler {handler.__class__.__name__} error: {e}")
                continue

        logger.warning(f"No handler found for update: chat_id={update.chat_id}")
        return None

    async def route_or_raise(self, update: TelegramUpdate, context: HandlerContext) -> str:
        """
        Route an update, raising if no handler found.
        """
        result = await self.route(update, context)
        if result is None:
            raise ValueError(f"No handler found for update type")
        return result


class HandlerRegistry:
    """
    Global registry for handler router.
    Provides convenient access to default router.
    """

    def __init__(self):
        self._router: Optional[HandlerRouter] = None

    def init_router(self, router: HandlerRouter) -> None:
        """Initialize with a router."""
        self._router = router

    @property
    def router(self) -> HandlerRouter:
        """Get the router, creating if needed."""
        if self._router is None:
            self._router = HandlerRouter()
        return self._router

    def register(self, handler: BaseHandler) -> None:
        """Register a handler on the default router."""
        self.router.register(handler)


_global_registry: Optional[HandlerRegistry] = None


def get_handler_registry() -> HandlerRegistry:
    """Get or create global handler registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = HandlerRegistry()
    return _global_registry