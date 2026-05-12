"""
NAS find folder tool.
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.synology_service import SynologyService


class NasFindFolderTool(BaseTool):
    """Find a folder by name on Synology NAS."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_find_folder"

    @property
    def description(self) -> str:
        return "Find a directory on Synology NAS by exact or partial name match. Searches globally if no folder specified."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Folder name or partial name to search for"
                },
                "folder_path": {
                    "type": "string",
                    "description": "Folder path to search in (default: searches globally)"
                }
            },
            "required": ["name"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        name = kwargs.get("name", "")
        folder_path = kwargs.get("folder_path")

        if not name:
            return ToolResult(success=False, error="Missing name")

        try:
            service = SynologyService.get_instance()
            result = service.find_folder(name=name, folder_path=folder_path)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))