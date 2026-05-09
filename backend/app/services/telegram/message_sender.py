"""
Telegram Message Sender

Sends messages to Telegram users.
"""

import httpx
import logging
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class MessageSenderService:
    """
    Service for sending messages via Telegram Bot API.

    Handles message formatting and delivery.
    """

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize message sender.

        Args:
            bot_token: Telegram bot token
        """
        from app.core.config import settings
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

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
        """
        Send text message to user.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Formatting mode (Markdown or HTML)
            disable_web_page_preview: Disable link previews
            disable_notification: Send silently
            reply_to_message_id: Reply to specific message
            reply_markup: Inline keyboard for buttons

        Returns:
            True if sent successfully
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": disable_web_page_preview,
                    "disable_notification": disable_notification,
                }
                if reply_to_message_id:
                    payload["reply_to_message_id"] = reply_to_message_id
                if reply_markup:
                    payload["reply_markup"] = reply_markup

                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("ok", False)
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def send_notification(
        self,
        chat_id: str,
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> bool:
        """
        Send formatted notification.

        Args:
            chat_id: Telegram chat ID
            title: Notification title
            message: Notification body
            notification_type: Type (info, success, warning, error)

        Returns:
            True if sent successfully
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

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        disable_notification: bool = False
    ) -> bool:
        """
        Send photo to user.

        Args:
            chat_id: Telegram chat ID
            photo_url: URL of photo
            caption: Optional caption
            disable_notification: Send silently

        Returns:
            True if sent successfully
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
            logger.error(f"Failed to send photo: {e}")
            return False

    async def send_chat_action(
        self,
        chat_id: str,
        action: str = "typing"
    ) -> bool:
        """
        Send chat action indicator.

        Args:
            chat_id: Telegram chat ID
            action: Action type (typing, upload_photo, record_video, etc.)

        Returns:
            True if sent successfully
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"chat_id": chat_id, "action": action}

                response = await client.post(
                    f"{self.api_url}/sendChatAction",
                    json=payload
                )

                return response.status_code == 200 and response.json().get("ok", False)

        except Exception as e:
            logger.error(f"Failed to send chat action: {e}")
            return False

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get bot info."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_url}/getMe")
                if response.status_code == 200:
                    return response.json().get("result")
                return None
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None

    async def health_check(self) -> bool:
        """Check Telegram API connectivity."""
        try:
            bot_info = await self.get_me()
            return bot_info is not None and bot_info.get("is_bot", False)
        except Exception:
            return False

    async def set_my_commands(self, commands: list) -> bool:
        """Set bot command menu."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/setMyCommands",
                    json={"commands": commands}
                )
                return response.status_code == 200 and response.json().get("ok", False)
        except Exception as e:
            logger.error(f"Failed to set commands: {e}")
            return False