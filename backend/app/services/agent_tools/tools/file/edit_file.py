"""
Edit file tool.
"""

import os
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class EditTool(SyncTool):
    """Edit a file by replacing old_string with new_string."""

    META = {"category": "file", "max_calls_per_run": 3, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing a specific string with new content."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "old_string": {"type": "string", "description": "Exact string to find and replace"},
                "new_string": {"type": "string", "description": "Replacement string"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences (default False)"}
            },
            "required": ["file_path", "old_string", "new_string"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_string = kwargs.get("old_string")
        new_string = kwargs.get("new_string")
        replace_all = kwargs.get("replace_all", False)

        try:
            if not file_path:
                return ToolResult(success=False, error="Missing file_path")
            if not old_string:
                return ToolResult(success=False, error="Missing old_string")
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(file_path)
            if not os.path.exists(resolved_path):
                return ToolResult(success=False, error=f"File not found: {resolved_path}")

            with open(resolved_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult(success=False, error=f"String not found in file: {old_string[:50]}...")

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(success=True, data={
                "file_path": str(resolved_path),
                "replacements": new_content.count(new_string) if replace_all else 1
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))