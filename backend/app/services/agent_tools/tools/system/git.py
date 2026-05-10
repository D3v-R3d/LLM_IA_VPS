"""
Git tool.
"""

import subprocess
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool


class GitTool(SyncTool):
    """Execute git commands."""

    META = {"category": "system", "max_calls_per_run": 0, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return "Execute git commands (status, log, diff, etc.)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Git command to execute"},
                "repo_path": {"type": "string", "description": "Repository path (default: current directory)"}
            },
            "required": ["command"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        repo_path = kwargs.get("repo_path")

        if not command:
            return ToolResult(success=False, error="Missing command")

        cmd = f"git {command}"
        if repo_path:
            cmd = f"cd {repo_path} && {cmd}"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))