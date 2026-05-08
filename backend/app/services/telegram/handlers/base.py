"""
Base Handler Interface for Telegram Updates

Defines the contract for handling different types of Telegram updates.
Each handler only knows how to handle its specific update type.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TelegramUpdate:
    """Parsed Telegram update."""
    chat_id: str
    user_id: Optional[int]
    text: Optional[str]
    command: Optional[str]
    message_id: Optional[int]
    raw: dict

    @classmethod
    def from_dict(cls, data: dict) -> "TelegramUpdate":
        """Parse from Telegram webhook payload."""
        message = data.get("message", {})
        chat = message.get("chat", {})

        text = message.get("text")
        command = None
        if text and text.startswith("/"):
            parts = text.split(" ", 1)
            command = parts[0]
            text = parts[1] if len(parts) > 1 else None

        return cls(
            chat_id=str(chat.get("id", "")),
            user_id=message.get("from", {}).get("id"),
            text=text,
            command=command,
            message_id=message.get("message_id"),
            raw=data
        )

    @classmethod
    def from_callback(cls, callback_query: dict) -> "TelegramUpdate":
        """Parse from Telegram callback_query."""
        message = callback_query.get("message", {})
        chat = message.get("chat", {})

        return cls(
            chat_id=str(chat.get("id", "")),
            user_id=callback_query.get("from", {}).get("id"),
            text=callback_query.get("data"),
            command=None,
            message_id=message.get("message_id"),
            raw=callback_query
        )


class BaseHandler(ABC):
    """
    Abstract base class for Telegram update handlers.

    Each handler implementation:
    - Handles ONE type of update
    - Returns response text or None
    - NEVER directly sends Telegram messages (delegates to sender)
    """

    @abstractmethod
    async def can_handle(self, update: TelegramUpdate) -> bool:
        """Check if this handler can process the update."""
        pass

    @abstractmethod
    async def handle(self, update: TelegramUpdate, context: "HandlerContext") -> Optional[str]:
        """
        Handle the update and return response text.

        Args:
            update: Parsed Telegram update
            context: Handler context with services

        Returns:
            Response text to send back, or None for no response
        """
        pass


class HandlerContext:
    """
    Context passed to handlers containing all required services.

    Avoids handlers creating their own service instances.
    """

    def __init__(
        self,
        db,
        telegram_service,
        user_service,
        conversation_service=None,
        message_service=None,
    ):
        self.db = db
        self.telegram_service = telegram_service
        self.user_service = user_service
        self.conversation_service = conversation_service
        self.message_service = message_service
        self._services = {}

    def set(self, key: str, value) -> None:
        """Store a service in context."""
        self._services[key] = value

    def get(self, key: str, default=None):
        """Get a service from context."""
        return self._services.get(key, default)
