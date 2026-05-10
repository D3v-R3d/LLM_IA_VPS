"""
Write file tool.
"""

import os
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class WriteTool(SyncTool):
    """Write content to a file (creates or overwrites)."""

    META = {"category": "file", "max_calls_per_run": 0, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Will overwrite existing files."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "content": {"type": "string", "description": "Content to write to the file"}
            },
            "required": ["file_path", "content"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content", "")

        try:
            if not file_path:
                return ToolResult(success=False, error="Missing file_path")
            if not isinstance(content, str):
                return ToolResult(success=False, error="Content must be a string")
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(file_path)
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, data={
                "file_path": str(resolved_path),
                "bytes_written": len(content.encode('utf-8'))
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))