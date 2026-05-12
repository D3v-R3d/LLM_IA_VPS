"""
NAS list share tool.
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.synology_service import SynologyService


class NasListShareTool(BaseTool):
    """List all shares on the Synology NAS."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_list_share"

    @property
    def description(self) -> str:
        return "List all available shares on the Synology NAS."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            service = SynologyService.get_instance()
            result = service.list_shares()
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))