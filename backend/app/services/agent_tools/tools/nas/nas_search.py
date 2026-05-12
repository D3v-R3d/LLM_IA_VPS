"""
NAS search tool.
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.synology_service import SynologyService


class NasSearchTool(BaseTool):
    """Search files recursively on Synology NAS across all shares."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_search"

    @property
    def description(self) -> str:
        return "Recursively search for files on Synology NAS by keyword. Searches globally from / if no folder specified."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Folder path to search in (default: /, searches all shares globally)"
                },
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (filename or partial name)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search subfolders recursively (default: true)"
                }
            },
            "required": ["keyword"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        keyword = kwargs.get("keyword", "")
        folder_path = kwargs.get("folder_path")
        recursive = kwargs.get("recursive", True)

        if not keyword:
            return ToolResult(success=False, error="Missing keyword")

        try:
            service = SynologyService.get_instance()
            result = service.search(
                keyword=keyword,
                folder_path=folder_path,
                recursive=recursive,
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))