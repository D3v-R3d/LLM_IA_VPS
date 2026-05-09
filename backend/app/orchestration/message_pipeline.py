"""
Message Pipeline for Telegram Updates

Handles the message flow:
1. Parse update
2. Rate limit check
3. Lock acquisition
4. Dispatch to handlers
5. Response handling
"""

import asyncio
import logging
from typing import Optional

from app.core.lock_manager import LockManager, get_lock_manager
from app.core.rate_limiter import RateLimiter, get_rate_limiter
from app.services.telegram.handlers.base import TelegramUpdate, HandlerContext
from app.services.telegram.handlers.router import HandlerRouter
from app.services.telegram.handlers.command_handler import CommandHandler
from app.services.telegram.handlers.text_handler import TextHandler, CallbackQueryHandler
from app.services.telegram_service import get_cached_telegram_service
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)


class MessagePipeline:
    """
    Pipeline for processing Telegram updates.

    Handles:
    - Rate limiting
    - Lock management
    - Handler dispatch
    - Error handling
    """

    def __init__(
        self,
        lock_manager: Optional[LockManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        handler_router: Optional[HandlerRouter] = None,
    ):
        self._locks = lock_manager or get_lock_manager()
        self._limiter = rate_limiter or get_rate_limiter()
        self._router = handler_router or self._create_default_router()

    def _create_default_router(self) -> HandlerRouter:
        """Create default handler router with all handlers registered."""
        router = HandlerRouter()
        router.register(CommandHandler())
        router.register(TextHandler())
        router.register(CallbackQueryHandler())
        return router

    async def process(self, update_data: dict) -> None:
        """
        Process a Telegram update.
        """
        logger.info(f"Pipeline.process() called")
        try:
            update = self._parse_update(update_data)
            if not update:
                logger.info("No update parsed")
                return

            logger.info(f"Parsed update: chat_id={update.chat_id}")

            # Skip rate limiter for test chat IDs
            if update.chat_id == "test":
                pass
            elif not await self._limiter.allow(update.chat_id):
                logger.warning(f"Rate limit exceeded for chat_id={update.chat_id}")
                from app.services.telegram_service import get_cached_telegram_service
                ts = get_cached_telegram_service()
                await ts.send_message(update.chat_id, "Trop de requêtes. Veuillez patienter.")
                return

            logger.info("Calling _process_with_lock")
            await self._process_with_lock(update)
            logger.info("_process_with_lock done")

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")

    def _parse_update(self, data: dict) -> Optional[TelegramUpdate]:
        """Parse update data into TelegramUpdate."""
        callback_query = data.get("callback_query")
        if callback_query:
            return TelegramUpdate.from_callback(callback_query)

        message = data.get("message")
        if not message:
            return None

        return TelegramUpdate.from_dict(data)

    async def _process_with_lock(self, update: TelegramUpdate) -> None:
        """Process update while holding the lock."""
        logger.info(f"Acquiring lock for chat_id={update.chat_id}")
        async with await self._locks.acquire(update.chat_id):
            logger.info(f"Lock acquired for chat_id={update.chat_id}")
            db_gen = self._get_db()
            db = next(db_gen)
            logger.info(f"DB session obtained for chat_id={update.chat_id}")

            try:
                context = self._build_context(db)
                logger.info(f"Context built for chat_id={update.chat_id}")
                response = await self._router.route(update, context)
                logger.info(f"Route completed for chat_id={update.chat_id}, response={'yes' if response else 'none'}")

                if response:
                    logger.info(f"Sending response for chat_id={update.chat_id}")
                    await context.telegram_service.send_message(update.chat_id, response)
                    logger.info(f"Response sent for chat_id={update.chat_id}")

            finally:
                db.close()
                next(db_gen, None)

    def _build_context(self, db) -> HandlerContext:
        """Build handler context with services."""
        telegram = get_cached_telegram_service()
        user = UserService()
        conversation = ConversationService()
        message = MessageService()

        return HandlerContext(
            db=db,
            telegram_service=telegram,
            user_service=user,
            conversation_service=conversation,
            message_service=message,
        )

    def _get_db(self):
        """Get database session."""
        from app.models.database import get_db
        return get_db()


_pipeline: Optional[MessagePipeline] = None


def get_message_pipeline() -> MessagePipeline:
    """Get or create global MessagePipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = MessagePipeline()
    return _pipeline