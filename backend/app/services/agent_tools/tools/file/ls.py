"""
List directory tool.
"""

import os
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class ListDirTool(SyncTool):
    """List contents of a directory."""

    META = {"category": "file", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "ls"

    @property
    def description(self) -> str:
        return "List contents of a directory."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"}
            }
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")

        try:
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(path)
            if not os.path.exists(resolved_path):
                return ToolResult(success=False, error=f"Path not found: {resolved_path}")

            if not os.path.isdir(resolved_path):
                return ToolResult(success=False, error=f"Not a directory: {resolved_path}")

            entries = os.listdir(resolved_path)
            entries_info = []
            for entry in entries:
                full_path = os.path.join(resolved_path, entry)
                is_dir = os.path.isdir(full_path)
                entries_info.append({
                    "name": entry,
                    "type": "dir" if is_dir else "file",
                    "size": os.path.getsize(full_path) if not is_dir else 0
                })

            entries_info.sort(key=lambda x: (x["type"], x["name"]))
            return ToolResult(success=True, data={"entries": entries_info, "count": len(entries)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))