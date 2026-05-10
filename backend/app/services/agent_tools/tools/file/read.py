"""
Read file tool.
"""

import os
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class ReadTool(SyncTool):
    """Read contents of a file."""

    META = {"category": "file", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read contents of a file. Returns the full content or a specific line range."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "offset": {"type": "integer", "description": "Line number to start reading from (1-indexed)"},
                "limit": {"type": "integer", "description": "Maximum number of lines to read"}
            },
            "required": ["file_path"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit")

        try:
            if not file_path:
                return ToolResult(success=False, error="Missing file_path")
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(file_path)
            if not os.path.exists(resolved_path):
                return ToolResult(success=False, error=f"File not found: {resolved_path}")

            if os.path.isdir(resolved_path):
                entries = os.listdir(resolved_path)
                content = "\n".join(entries)
                return ToolResult(success=True, data={"type": "directory", "content": content})

            with open(resolved_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start = max(0, offset - 1)
            end = start + limit if limit else len(lines)

            content = "".join(lines[start:end])
            return ToolResult(success=True, data={
                "content": content,
                "total_lines": total_lines,
                "offset": offset,
                "limit": limit
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))