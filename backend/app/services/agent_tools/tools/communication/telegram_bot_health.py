"""
Telegram Bot Health Tool
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.telegram_service import get_cached_telegram_service


telegram_service = get_cached_telegram_service()


class TelegramBotHealthTool(BaseTool):
    """Check Telegram bot health."""

    META = {"category": "communication", "max_calls_per_run": 0, "parallel_safe": True}

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