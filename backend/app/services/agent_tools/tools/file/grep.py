"""
Grep tool.
"""

import os
import re
import glob as glob_module
from pathlib import Path
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.services.agent_tools.utils.path_guard import resolve as path_guard_resolve


class GrepTool(SyncTool):
    """Search for text in files."""

    META = {"category": "file", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search for text/regex pattern in files. Returns file paths and line numbers."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex or text pattern to search for"},
                "path": {"type": "string", "description": "Directory to search in"},
                "include": {"type": "string", "description": "File pattern to include (e.g., *.py, *.js)"}
            },
            "required": ["pattern"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern")
        base_path = kwargs.get("path", ".")
        include = kwargs.get("include")

        try:
            if not pattern:
                return ToolResult(success=False, error="Missing pattern")
            # Use PathGuard to restrict to allowed paths
            resolved_path = path_guard_resolve(base_path)
            regex = re.compile(pattern)
            results = []

            for root, dirs, files in os.walk(resolved_path):
                # Skip common non-relevant directories
                if ".git" in root or "node_modules" in root or "__pycache__" in root:
                    continue

                for file in files:
                    if include and not glob_module.fnmatch.fnmatch(file, include):
                        continue

                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    results.append({
                                        "file": file_path,
                                        "line": line_num,
                                        "content": line.rstrip()
                                    })
                    except Exception:
                        continue

            return ToolResult(success=True, data={"results": results, "count": len(results)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))