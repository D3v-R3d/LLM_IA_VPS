"""
Glob tool.
"""

import os
import glob as glob_module
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class GlobTool(SyncTool):
    """Find files by glob pattern."""

    META = {"category": "file", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern (e.g., **/*.py, **/*.js)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern to match (e.g., **/*.py)"},
                "path": {"type": "string", "description": "Base path to search from (default: current directory)"}
            },
            "required": ["pattern"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern")
        base_path = kwargs.get("path", ".")

        try:
            if not pattern:
                return ToolResult(success=False, error="Missing pattern")
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(base_path)
            matches = glob_module.glob(pattern, root_dir=resolved_path)
            matches.sort()
            return ToolResult(success=True, data={"matches": matches, "count": len(matches)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))