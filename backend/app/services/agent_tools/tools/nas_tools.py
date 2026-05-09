"""
NAS Synology Tools

Tools for interacting with Synology NAS file station.
"""

from typing import Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


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
            from app.services.synology import SynologyClient, SynologyAuth, FileStation
            client = SynologyClient()
            auth = SynologyAuth(client)
            auth.login()
            nas = FileStation(client)
            result = nas.list_shares()
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
            "required": ["folder_path"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from app.services.synology import SynologyClient, SynologyAuth, FileStation
            folder_path = kwargs.get("folder_path", "/")
            client = SynologyClient()
            auth = SynologyAuth(client)
            auth.login()
            nas = FileStation(client)
            result = nas.list_folders(folder_path=folder_path)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class NasSearchTool(BaseTool):
    """Search files on Synology NAS."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_search"

    @property
    def description(self) -> str:
        return "Search for files on Synology NAS by keyword."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Folder path to search in"
                },
                "keyword": {
                    "type": "string",
                    "description": "Search keyword"
                }
            },
            "required": ["folder_path", "keyword"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from app.services.synology import SynologyClient, SynologyAuth, FileStation
            folder_path = kwargs.get("folder_path", "/")
            keyword = kwargs.get("keyword", "")
            client = SynologyClient()
            auth = SynologyAuth(client)
            auth.login()
            nas = FileStation(client)
            result = nas.search(folder_path=folder_path, keyword=keyword)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))