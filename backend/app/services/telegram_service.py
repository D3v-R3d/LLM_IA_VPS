"""
Telegram Service

Unified interface for Telegram bot functionality.
Uses services from app.services.telegram subfolder.
"""

from typing import Optional, Dict, Any
import httpx
import logging
import threading

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


class TelegramService:
    """
    Unified Telegram bot service.

    Combines:
    - WebhookHandlerService: Webhook verification and parsing
    - MessageSenderService: Sending messages

    Use get_cached_telegram_service() for singleton access.
    """

    def __init__(self, bot_token: Optional[str] = None):
        """Initialize with sub-services."""
        from app.core.config import settings
        from app.services.telegram import (
            WebhookHandlerService,
            MessageSenderService
        )

        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        self.webhook = WebhookHandlerService()
        self.sender = MessageSenderService(bot_token=self.bot_token)

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

    def verify_webhook(self, secret_token: Optional[str] = None) -> bool:
        """Verify webhook request."""
        return self.webhook.verify_webhook(secret_token)

    def parse_command(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse command from message text."""
        return self.webhook.extract_command(text)

    async def set_webhook(self, url: str, secret_token: Optional[str] = None) -> bool:
        """Set webhook URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"url": url, "max_connections": 100}
                if secret_token:
                    payload["secret_token"] = secret_token

                response = await client.post(
                    f"{self.api_url}/setWebhook",
                    json=payload
                )

                result = response.json()
                return result.get("ok", False) and result.get("result", False)

        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.api_url}/deleteWebhook")
                result = response.json()
                return result.get("ok", False)
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False

    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get webhook info."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_url}/getWebhookInfo")
                if response.status_code == 200:
                    return response.json().get("result")
                return None
        except Exception as e:
            logger.error(f"Failed to get webhook info: {e}")
            return None

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get bot info."""
        return await self.sender.get_me()

    async def health_check(self) -> bool:
        """Check Telegram API connectivity."""
        return await self.sender.health_check()

    async def set_my_commands(self, commands: list) -> bool:
        """Set bot command menu."""
        return await self.sender.set_my_commands(commands)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """Answer callback query."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"callback_query_id": callback_query_id}
                if text:
                    payload["text"] = text
                    payload["show_alert"] = show_alert

                response = await client.post(
                    f"{self.api_url}/answerCallbackQuery",
                    json=payload
                )

                return response.status_code == 200 and response.json().get("ok", False)
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")
            return False

    async def send_welcome_message(self, chat_id: str) -> bool:
        """Send welcome message."""
        text = (
            "*Welcome to Tower Bot!*\n\n"
            "Your AI assistant with NAS access.\n\n"
            "*Commands:*\n"
            "/nas - List NAS shares\n"
            "/ls <folder> - Browse NAS folders\n"
            "/naslogin - Connect to NAS\n"
            "/model - List/switch AI models (/model list, /model switch <id>)\n"
            "/status - Check your account\n"
            "/help - Show this help\n"
        )
        return await self.send_message(chat_id, text)

    async def send_help_message(self, chat_id: str) -> bool:
        """Send help message."""
        text = (
            "*Tower Bot Help*\n\n"
            "*AI Commands (via chat):*\n"
            "Ask me anything! I have access to:\n"
            "• Web search & fetch URLs\n"
            "• NAS file browsing\n"
            "• Database queries\n"
            "• File operations (read, write, edit)\n"
            "• System commands (bash, docker, git)\n\n"
            "*Direct Commands:*\n"
            "/nas - List all shared folders on NAS\n"
            "/ls <folder> - List files in folder\n"
            "/naslogin - Connect to Synology NAS\n"
            "/status - Check connection status\n"
            "/link <email> - Link your account\n"
            "/unlink - Unlink your account\n"
            "/new - Start new session\n"
            "/reset - Clear conversation\n"
            "/compress - Summarize conversation\n"
            "/sessions - List your sessions\n"
            "/prefs - Show preferences\n"
            "/setpref key=value - Set preference\n"
            "/model - Switch AI model\n\n"
            "*Messaging:*\n"
            "Just type your message to chat with Tower!\n"
            "Example: \"list my nas folders\" or \"search web for python\"\n"
        )
        return await self.send_message(chat_id, text)