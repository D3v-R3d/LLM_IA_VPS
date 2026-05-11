"""
Telegram Service - Pure Facade

Unified interface for Telegram bot functionality.
All calls delegated to sub-services in app.services.telegram subfolder.

Single source of truth:
- MessageSenderService: send_message, send_notification, send_chat_action, send_photo,
                       get_me, health_check, set_my_commands, answer_callback_query
- WebhookHandlerService: verify_webhook, set_webhook, delete_webhook, get_webhook_info,
                         extract_command, extract_chat_id, extract_message_text, parse_update
- CommandParserService: parse, handle, register (command routing)
"""

import logging
import threading
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_service_cache: Optional["TelegramService"] = None
_cache_lock = threading.Lock()


def get_cached_telegram_service() -> "TelegramService":
    """Get or create singleton TelegramService instance."""
    global _service_cache
    if _service_cache is None:
        with _cache_lock:
            if _service_cache is None:
                _service_cache = TelegramService()
    return _service_cache


@dataclass
class CommandResult:
    """Result of command parsing."""
    command: str
    args: Optional[str]
    handled: bool
    response: Optional[str] = None


class TelegramService:
    """
    Unified Telegram bot service - PURE FACADE.

    All implementation delegated to sub-services.
    NO business logic, NO direct HTTP calls.

    Use get_cached_telegram_service() for singleton access.
    """

    def __init__(self, bot_token: Optional[str] = None):
        """Initialize with sub-services."""
        from app.core.config import settings
        from app.services.telegram import (
            WebhookHandlerService,
            MessageSenderService,
            CommandParserService,
        )

        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN

        self.webhook = WebhookHandlerService(bot_token=self.bot_token)
        self.sender = MessageSenderService(bot_token=self.bot_token)
        self.parser = CommandParserService()

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Any] = None
    ) -> bool:
        """Send text message."""
        return await self.sender.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup
        )

    async def send_notification(
        self,
        chat_id: str,
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> bool:
        """Send formatted notification."""
        return await self.sender.send_notification(
            chat_id=chat_id,
            title=title,
            message=message,
            notification_type=notification_type
        )

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        """Send chat action."""
        return await self.sender.send_chat_action(chat_id=chat_id, action=action)

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        disable_notification: bool = False
    ) -> bool:
        """Send photo."""
        return await self.sender.send_photo(
            chat_id=chat_id,
            photo_url=photo_url,
            caption=caption,
            disable_notification=disable_notification
        )

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """Answer callback query."""
        return await self.sender.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert
        )

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get bot info."""
        return await self.sender.get_me()

    async def health_check(self) -> bool:
        """Check Telegram API connectivity."""
        return await self.sender.health_check()

    async def set_my_commands(self, commands: list) -> bool:
        """Set bot command menu."""
        return await self.sender.set_my_commands(commands)

    def verify_webhook(self, secret_token: Optional[str] = None) -> bool:
        """Verify webhook request."""
        return self.webhook.verify_webhook(secret_token)

    async def set_webhook(self, url: str, secret_token: Optional[str] = None) -> bool:
        """Set webhook URL."""
        return await self.webhook.set_webhook(url, secret_token)

    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        return await self.webhook.delete_webhook()

    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get webhook info."""
        return await self.webhook.get_webhook_info()

    def parse_command(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse command from message text."""
        return self.parser.parse(text)

    def register_command(
        self,
        command: str,
        handler: Callable[[Optional[str]], Awaitable[CommandResult]]
    ) -> None:
        """Register a command handler."""
        self.parser.register(command, handler)

    async def handle_command(self, text: str) -> Optional[CommandResult]:
        """Handle command and return result."""
        return await self.parser.handle(text)
