"""
Telegram Webhook Handler

Handles incoming Telegram webhook updates.
"""

import hmac
import httpx
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.core.config import settings


logger = logging.getLogger(__name__)


class TelegramUpdate(BaseModel):
    """Telegram update model."""
    update_id: int
    message: Optional[Dict[str, Any]] = None


class WebhookHandlerService:
    """
    Service for handling Telegram webhook requests.

    Verifies webhook authenticity, parses updates, and manages webhook URL.
    """

    def __init__(self, bot_token: Optional[str] = None):
        from app.core.config import settings
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def verify_webhook(self, secret_token: Optional[str] = None) -> bool:
        """
        Verify webhook request is from Telegram.

        Args:
            secret_token: Secret token from X-Telegram-Bot-Api-Secret-Token header

        Returns:
            True if verification passes
        """
        expected = settings.TELEGRAM_SECRET_TOKEN

        if not expected:
            logger.error("TELEGRAM_SECRET_TOKEN not configured")
            return False

        if not secret_token:
            return False

        return hmac.compare_digest(secret_token, expected)

    def parse_update(self, update_data: Dict[str, Any]) -> Optional[TelegramUpdate]:
        """
        Parse raw update data into TelegramUpdate.

        Args:
            update_data: Raw update dictionary from Telegram

        Returns:
            Parsed TelegramUpdate or None if invalid
        """
        try:
            return TelegramUpdate(**update_data)
        except Exception:
            return None

    def extract_message_text(self, update: TelegramUpdate) -> Optional[str]:
        """
        Extract text from update message.

        Args:
            update: Parsed Telegram update

        Returns:
            Message text or None
        """
        if update.message:
            return update.message.get("text")
        return None

    def extract_chat_id(self, update: TelegramUpdate) -> Optional[int]:
        """
        Extract chat ID from update.

        Args:
            update: Parsed Telegram update

        Returns:
            Chat ID or None
        """
        if update.message:
            chat = update.message.get("chat", {})
            return chat.get("id")
        return None

    def extract_command(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract command and arguments from message text.

        Args:
            text: Message text

        Returns:
            Tuple of (command, arguments)
        """
        if not text or not text.startswith("/"):
            return None, None

        parts = text.split(" ", 1)
        command = parts[0][1:].lower()
        args = parts[1] if len(parts) > 1 else None

        if "@" in command:
            command = command.split("@")[0]

        return command, args

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