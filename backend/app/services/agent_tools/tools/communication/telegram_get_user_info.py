"""
Telegram Get User Info Tool
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.telegram_service import get_cached_telegram_service


telegram_service = get_cached_telegram_service()


class TelegramGetUserInfoTool(BaseTool):
    """Get Telegram user info."""

    META = {"category": "communication", "max_calls_per_run": 0, "parallel_safe": True}

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

        if not chat_id:
            return ToolResult(success=False, error="Missing chat_id")

        try:
            info = await telegram_service.get_user_info(chat_id)
            return ToolResult(success=True, data=info)
        except Exception as e:
            return ToolResult(success=False, error=str(e))