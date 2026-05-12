"""
Telegram Send Message Tool
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.telegram_service import get_cached_telegram_service


telegram_service = get_cached_telegram_service()


class TelegramSendMessageTool(BaseTool):
    """Send a message via Telegram."""

    META = {"category": "communication", "max_calls_per_run": 0, "parallel_safe": True}

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

        if not chat_id:
            return ToolResult(success=False, error="Missing chat_id")
        if not text:
            return ToolResult(success=False, error="Missing text")

        try:
            success = await telegram_service.send_message(chat_id, text)
            return ToolResult(success=success, data={"chat_id": chat_id, "sent": success})
        except Exception as e:
            return ToolResult(success=False, error=str(e))