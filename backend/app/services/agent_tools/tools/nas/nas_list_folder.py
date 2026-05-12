"""
NAS list folder tool.
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.synology_service import SynologyService


class NasListFolderTool(BaseTool):
    """List contents of a folder on Synology NAS."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_list_folder"

    @property
    def description(self) -> str:
        return "List contents of a folder on Synology NAS."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Folder path on NAS (e.g. /chat or /PlexMediaServer)"
                }
            },
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        folder_path = kwargs.get("folder_path", "/")

        try:
            service = SynologyService.get_instance()
            result = service.list_folder(folder_path=folder_path)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))