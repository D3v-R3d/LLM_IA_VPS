"""
System Tools - Bash, Docker, Git, Pkill

Tools for system operations.
"""

import subprocess
import socket
import json
from typing import Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult, SyncTool


class DockerTool(SyncTool):
    """Execute docker commands using Docker socket API."""

    META = {"category": "system", "max_calls_per_run": 0, "parallel_safe": False}

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
                "command": {"type": "string", "description": "Docker command to execute (without 'docker' prefix)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
            },
            "required": ["command"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 30)

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect("/var/run/docker.sock")

            path = "/containers/json"
            method = "GET"

            if command.startswith("ps"):
                path = "/containers/json?all=1"
            elif command.startswith("images"):
                path = "/images/json"
            elif command.startswith("logs"):
                parts = command.split()
                container_id = parts[1] if len(parts) > 1 else ""
                if container_id and len(container_id) < 64:
                    path = f"/containers/{container_id}/logs?stdout=1&stderr=1"
                else:
                    return ToolResult(success=False, error="Invalid container ID for logs")
            elif command.startswith("inspect"):
                parts = command.split()
                container_id = parts[1] if len(parts) > 1 else ""
                if container_id:
                    path = f"/containers/{container_id}/json"
            elif command.startswith("stats"):
                path = "/containers/stats?stream=0"
            elif command.startswith("version"):
                path = "/version"
            else:
                path = "/containers/json?all=1"

            request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            sock.send(request.encode())

            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if len(response) > 50000:
                        response += b"\n[Output truncated]"
                        break
                except socket.timeout:
                    break

            sock.close()

            if b"\r\n\r\n" in response:
                body = response.split(b"\r\n\r\n", 1)[1]
                if body.startswith(b"0\r\n") or body.startswith(b"0"):
                    body = body.split(b"\r\n", 1)[1] if b"\r\n" in body else body
                    body = body.split(b"\r\n", 1)[1] if b"\r\n" in body else body
                decoded = self._decode_chunked(body)
                return ToolResult(success=True, data={"response": decoded[:40000]})
            else:
                return ToolResult(success=True, data={"raw_response": response.decode("utf-8", errors="replace")[:40000]})

        except socket.timeout:
            return ToolResult(success=False, error=f"Docker command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _decode_chunked(self, body: bytes) -> str:
        """Decode HTTP chunked transfer encoding."""
        try:
            if b"\r\n" not in body:
                return body.decode("utf-8", errors="replace")
            result = b""
            while body:
                line, body = body.split(b"\r\n", 1)
                if not line:
                    break
                try:
                    chunk_size = int(line, 16)
                except ValueError:
                    break
                if chunk_size == 0:
                    break
                result += body[:chunk_size]
                body = body[chunk_size:]
                if body.startswith(b"\r\n"):
                    body = body[2:]
            return result.decode("utf-8", errors="replace")
        except Exception:
            return body.decode("utf-8", errors="replace")


class BashTool(SyncTool):
    """Execute a bash command."""

    META = {"category": "system", "max_calls_per_run": 1, "parallel_safe": False}

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