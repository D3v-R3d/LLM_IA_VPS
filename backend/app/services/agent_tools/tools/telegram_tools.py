"""
Telegram Tools - SendMessage, SendNotification, GetUserInfo, BotHealth

Tools for Telegram bot operations.
"""

from typing import Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult
from app.services.telegram_service import get_cached_telegram_service


telegram_service = get_cached_telegram_service()


class TelegramSendMessageTool(BaseTool):
    """Send a message via Telegram."""

    @property
    def name(self) -> str:
        return "telegram_send_message"

    @property
    def description(self) -> str:
        return "Send a text message via Telegram bot."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Telegram chat ID"},
                "text": {"type": "string", "description": "Message text to send"}
            },
            "required": ["chat_id", "text"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        chat_id = kwargs.get("chat_id")
        text = kwargs.get("text")
        
        try:
            success = await telegram_service.send_message(chat_id, text)
            return ToolResult(success=success, data={"chat_id": chat_id, "sent": success})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TelegramSendNotificationTool(BaseTool):
    """Send a notification via Telegram."""

    @property
    def name(self) -> str:
        return "telegram_send_notification"

    @property
    def description(self) -> str:
        return "Send a styled notification via Telegram bot."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Telegram chat ID"},
                "title": {"type": "string", "description": "Notification title"},
                "message": {"type": "string", "description": "Notification body"},
                "notification_type": {"type": "string", "description": "Type: success, error, info, warning"}
            },
            "required": ["chat_id", "title", "message"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        chat_id = kwargs.get("chat_id")
        title = kwargs.get("title")
        message = kwargs.get("message")
        notification_type = kwargs.get("notification_type", "info")
        
        try:
            success = await telegram_service.send_notification(chat_id, title, message, notification_type)
            return ToolResult(success=success, data={"chat_id": chat_id, "sent": success})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TelegramGetUserInfoTool(BaseTool):
    """Get Telegram user info."""

    @property
    def name(self) -> str:
        return "telegram_get_user_info"

    @property
    def description(self) -> str:
        return "Get information about a Telegram user by chat_id."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Telegram chat ID"}
            },
            "required": ["chat_id"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        chat_id = kwargs.get("chat_id")
        
        try:
            info = await telegram_service.get_user_info(chat_id)
            return ToolResult(success=True, data=info)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TelegramBotHealthTool(BaseTool):
    """Check Telegram bot health."""

    @property
    def name(self) -> str:
        return "telegram_bot_health"

    @property
    def description(self) -> str:
        return "Check if Telegram bot is working and get bot info."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        try:
            healthy = await telegram_service.health_check()
            bot_info = await telegram_service.get_me()
            return ToolResult(success=healthy, data={"healthy": healthy, "bot_info": bot_info})
        except Exception as e:
            return ToolResult(success=False, error=str(e))