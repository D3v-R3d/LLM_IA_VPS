"""
Synology NAS tools - Thin wrappers around SynologyService.

These tools contain NO Synology logic. They delegate to SynologyService.
"""

from typing import Optional

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


class NasFindFileTool(BaseTool):
    """Find a file by name on Synology NAS."""

    META = {"category": "nas", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "nas_find_file"

    @property
    def description(self) -> str:
        return "Find a file on Synology NAS by exact or partial name match. Searches globally if no folder specified."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Filename or partial name to search for"
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
            result = service.find_file(name=name, folder_path=folder_path)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
