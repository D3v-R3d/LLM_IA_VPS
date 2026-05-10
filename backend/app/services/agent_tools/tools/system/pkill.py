"""
Pkill tool.
"""

import subprocess
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool


class PkillTool(SyncTool):
    """Kill processes by name."""

    META = {"category": "system", "max_calls_per_run": 0, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "pkill"

    @property
    def description(self) -> str:
        return "Kill processes by name or pattern."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Process name or pattern to kill"},
                "force": {"type": "boolean", "description": "Force kill (-9)"}
            },
            "required": ["pattern"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern")
        force = kwargs.get("force", False)

        if not pattern:
            return ToolResult(success=False, error="Missing pattern")

        signal = "-9" if force else ""
        cmd = f"pkill {signal} -f {pattern}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return ToolResult(
                success=result.returncode == 0,
                data={"killed": result.returncode == 0, "output": result.stdout or result.stderr}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))