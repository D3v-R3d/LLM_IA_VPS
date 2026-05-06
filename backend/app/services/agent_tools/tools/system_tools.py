"""
System Tools - Bash, Docker, Git, Pkill

Tools for system operations.
"""

import subprocess
from typing import Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult, SyncTool


class BashTool(SyncTool):
    """Execute a bash command."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a bash command in the terminal. Returns command output."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
            },
            "required": ["command"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DockerTool(SyncTool):
    """Execute docker commands."""

    @property
    def name(self) -> str:
        return "docker"

    @property
    def description(self) -> str:
        return "Execute docker commands (ps, images, logs, etc.)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Docker command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
            },
            "required": ["command"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        if not command.startswith("docker"):
            command = f"docker {command}"
        timeout = kwargs.get("timeout", 30)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GitTool(SyncTool):
    """Execute git commands."""

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


class PkillTool(SyncTool):
    """Kill processes by name."""

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