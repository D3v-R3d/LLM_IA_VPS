"""
Docker tool.
"""

import socket
from typing import Optional

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool


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
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 10)"}
            },
            "required": ["command"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 10)

        if not command:
            return ToolResult(success=False, error="Missing command")

        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect("/var/run/docker.sock")

            path = "/containers/json"
            method = "GET"

            cmd_lower = command.lower().strip()
            if cmd_lower.startswith("ps") or cmd_lower == "ps":
                path = "/containers/json?all=1"
            elif cmd_lower.startswith("images") or cmd_lower == "images":
                path = "/images/json"
            elif cmd_lower.startswith("logs"):
                parts = command.split()
                container_id = parts[1] if len(parts) > 1 else ""
                if container_id and len(container_id) < 64:
                    path = f"/containers/{container_id}/logs?stdout=1&stderr=1&tail=50"
                else:
                    return ToolResult(success=False, error="Invalid container ID for logs")
            elif cmd_lower.startswith("inspect"):
                parts = command.split()
                container_id = parts[1] if len(parts) > 1 else ""
                if container_id:
                    path = f"/containers/{container_id}/json"
            elif cmd_lower.startswith("stats"):
                path = "/containers/stats?stream=false"
            elif cmd_lower.startswith("version") or cmd_lower == "version":
                path = "/version"
            elif cmd_lower.startswith("info") or cmd_lower == "info":
                path = "/info"
            elif cmd_lower.startswith("networks") or cmd_lower == "networks":
                path = "/networks"
            elif cmd_lower.startswith("volumes") or cmd_lower == "volumes":
                path = "/volumes"
            else:
                path = "/containers/json?all=1"

            request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            sock.sendall(request.encode())

            response = b""
            while True:
                try:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    response += chunk
                    if len(response) > 50000:
                        response += b"\n[Output truncated]"
                        break
                except socket.timeout:
                    break

        except socket.timeout:
            return ToolResult(success=False, error=f"Docker command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

        if not response:
            return ToolResult(success=False, error="Empty response from Docker")

        if b"\r\n\r\n" in response:
            body = response.split(b"\r\n\r\n", 1)[1]
            if body.startswith(b"0\r\n") or body.startswith(b"0"):
                parts = body.split(b"\r\n", 2)
                if len(parts) >= 3:
                    body = parts[2]
                elif len(parts) == 2:
                    body = parts[1]
            decoded = self._decode_chunked(body)
            return ToolResult(success=True, data={"response": decoded[:40000]})
        else:
            return ToolResult(success=True, data={"raw_response": response.decode("utf-8", errors="replace")[:40000]})

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