"""
Telegram Bot Service Module

Handles interactions with Telegram Bot API for notifications and bidirectional messaging.

Features:
- Send text messages to users via Telegram
- Webhook endpoint for receiving messages from Telegram
- Store user's Telegram chat_id for notifications
- Handle /start command to link Telegram to user account

Usage:
    from app.services.telegram_service import TelegramService

    telegram = TelegramService()
    telegram.send_message(chat_id="123456789", text="Hello!")
"""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


class TelegramChat(BaseModel):
    id: int
    type: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None


class TelegramMessage(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = None
    chat: TelegramChat
    text: Optional[str] = None
    date: int
    entities: Optional[List[Dict[str, Any]]] = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None


class TelegramResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    error_code: Optional[int] = None


class TelegramService:
    """
    Telegram Bot API service.

    Provides methods for sending messages and handling webhook updates.
    """

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram service.

        Args:
            bot_token: Telegram bot token. Defaults to TELEGRAM_BOT_TOKEN env var.
        """
        from app.core.config import settings

        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.file_url = f"https://api.telegram.org/file/bot{self.bot_token}"

    def verify_webhook(self, secret_token: Optional[str] = None) -> bool:
        """
        Verify webhook request is from Telegram.

        Args:
            secret_token: Expected secret token from X-Telegram-Bot-Api-Secret-Token header

        Returns:
            True if verification passes, False otherwise
        """
        if not secret_token:
            return True
        from app.core.config import settings
        expected = settings.TELEGRAM_SECRET_TOKEN
        if not expected:
            return True
        return hmac.compare_digest(secret_token, expected)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """
        Send a text message to a Telegram user.

        Args:
            chat_id: Telegram chat ID (as string)
            text: Message text (supports Markdown formatting)
            parse_mode: Formatting mode ("Markdown" or "HTML")
            disable_web_page_preview: Disable link previews
            disable_notification: Send silently
            reply_to_message_id: Reply to specific message

        Returns:
            True if message sent successfully, False otherwise

        Example:
            success = await telegram.send_message(
                chat_id="123456789",
                text="Hello from Tower!"
            )
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                    "disable_notification": disable_notification,
                }
                if reply_to_message_id:
                    payload["reply_to_message_id"] = reply_to_message_id

                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("ok", False)
                else:
                    logger.error(f"Telegram API error: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_chat_action(
        self,
        chat_id: str,
        action: str = "typing"
    ) -> bool:
        """
        Send a chat action to indicate activity.

        Args:
            chat_id: Telegram chat ID
            action: Type of action (typing, upload_photo, record_video, etc.)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "chat_id": chat_id,
                    "action": action
                }

                response = await client.post(
                    f"{self.api_url}/sendChatAction",
                    json=payload
                )

                return response.status_code == 200 and response.json().get("ok", False)

        except Exception as e:
            logger.error(f"Failed to send chat action: {e}")
            return False

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        disable_notification: bool = False
    ) -> bool:
        """
        Send a photo to a Telegram user.

        Args:
            chat_id: Telegram chat ID
            photo_url: URL of the photo
            caption: Optional caption
            disable_notification: Send silently

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "chat_id": chat_id,
                    "photo": photo_url,
                    "disable_notification": disable_notification,
                }
                if caption:
                    payload["caption"] = caption

                response = await client.post(
                    f"{self.api_url}/sendPhoto",
                    json=payload
                )

                return response.status_code == 200 and response.json().get("ok", False)

        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            return False

    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        caption: Optional[str] = None,
        disable_notification: bool = False
    ) -> bool:
        """
        Send a document to a Telegram user.

        Args:
            chat_id: Telegram chat ID
            document_url: URL of the document
            caption: Optional caption
            disable_notification: Send silently

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "chat_id": chat_id,
                    "document": document_url,
                    "disable_notification": disable_notification,
                }
                if caption:
                    payload["caption"] = caption

                response = await client.post(
                    f"{self.api_url}/sendDocument",
                    json=payload
                )

                return response.status_code == 200 and response.json().get("ok", False)

        except Exception as e:
            logger.error(f"Failed to send Telegram document: {e}")
            return False

    async def set_webhook(
        self,
        url: str,
        secret_token: Optional[str] = None,
        max_connections: int = 100
    ) -> bool:
        """
        Set the webhook URL for receiving Telegram updates.

        Args:
            url: Full HTTPS URL for webhook (must be publicly accessible)
            secret_token: Optional secret token for verification
            max_connections: Max concurrent connections

        Returns:
            True if webhook set successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "url": url,
                    "max_connections": max_connections,
                }
                if secret_token:
                    payload["secret_token"] = secret_token

                response = await client.post(
                    f"{self.api_url}/setWebhook",
                    json=payload
                )

                result = response.json()
                return result.get("ok", False) and result.get("result", False)

        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """
        Delete the current webhook.

        Returns:
            True if webhook deleted successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.api_url}/deleteWebhook")
                result = response.json()
                return result.get("ok", False)

        except Exception as e:
            logger.error(f"Failed to delete Telegram webhook: {e}")
            return False

    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current webhook info.

        Returns:
            Dict with webhook info or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_url}/getWebhookInfo")
                if response.status_code == 200:
                    return response.json().get("result")
                return None

        except Exception as e:
            logger.error(f"Failed to get Telegram webhook info: {e}")
            return None

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """
        Get bot information.

        Returns:
            Dict with bot info (id, is_bot, first_name, username) or None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_url}/getMe")
                if response.status_code == 200:
                    return response.json().get("result")
                return None

        except Exception as e:
            logger.error(f"Failed to get Telegram bot info: {e}")
            return None

    async def get_updates(
        self,
        offset: Optional[int] = None,
        limit: int = 100,
        timeout: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get updates from Telegram (polling mode alternative to webhooks).

        Args:
            offset: Update ID to start from
            limit: Max number of updates to fetch
            timeout: Long polling timeout in seconds

        Returns:
            List of updates
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {"limit": limit, "timeout": timeout}
                if offset:
                    payload["offset"] = offset

                response = await client.post(
                    f"{self.api_url}/getUpdates",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        return result.get("result", [])
                return []

        except Exception as e:
            logger.error(f"Failed to get Telegram updates: {e}")
            return []

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """
        Answer a callback query from inline button.

        Args:
            callback_query_id: ID from callback query
            text: Text to show (optional)
            show_alert: Show as alert dialog instead of toast

        Returns:
            True if answered successfully, False otherwise
        """
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

    async def health_check(self) -> bool:
        """
        Verify Telegram API connectivity.

        Returns:
            True if bot token is valid and API is reachable, False otherwise
        """
        try:
            bot_info = await self.get_me()
            return bot_info is not None and bot_info.get("is_bot", False)
        except Exception:
            return False

    def parse_command(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse a command from message text.

        Args:
            text: Message text

        Returns:
            Tuple of (command, args) or (None, None) if not a command

        Example:
            cmd, args = parse_command("/start abc123")
            # cmd = "start", args = "abc123"
        """
        if not text or not text.startswith("/"):
            return None, None

        parts = text.split(" ", 1)
        command = parts[0][1:].lower()
        args = parts[1] if len(parts) > 1 else None

        return command, args

    async def send_welcome_message(self, chat_id: str, username: Optional[str] = None) -> bool:
        """
        Send welcome message with instructions.

        Args:
            chat_id: Telegram chat ID
            username: Bot username for deep linking

        Returns:
            True if sent successfully, False otherwise
        """
        welcome_text = (
            "*Welcome to Tower Bot!*\n\n"
            "I'll help you stay connected with your conversations.\n\n"
            "Available commands:\n"
            "/start - Register your Telegram account\n"
            "/help - Show help information\n"
            "/status - Check your connection status\n"
        )

        return await self.send_message(chat_id, welcome_text)

    async def send_help_message(self, chat_id: str) -> bool:
        """
        Send help message.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if sent successfully, False otherwise
        """
        help_text = (
            "*Tower Bot Help*\n\n"
            "This bot allows you to:\n"
            "- Receive notifications about your conversations\n"
            "- Send messages directly to Tower\n"
            "- Link your Telegram account to Tower\n\n"
            "To get started, use /start and enter your Tower email."
        )

        return await self.send_message(chat_id, help_text)

    async def send_notification(
        self,
        chat_id: str,
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> bool:
        """
        Send a formatted notification message.

        Args:
            chat_id: Telegram chat ID
            title: Notification title
            message: Notification body
            notification_type: Type of notification (info, success, warning, error)

        Returns:
            True if sent successfully, False otherwise
        """
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }

        emoji = emoji_map.get(notification_type, "ℹ️")

        text = f"{emoji} *{title}*\n\n{message}"

        return await self.send_message(chat_id, text)