"""
File Tools - Read, Write, Edit, Glob, Grep

Tools for file system operations.
"""

import os
import glob as glob_module
from pathlib import Path
from typing import List, Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult, SyncTool


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
            if not os.path.exists(file_path):
                return ToolResult(success=False, error=f"File not found: {file_path}")

            if os.path.isdir(file_path):
                entries = os.listdir(file_path)
                content = "\n".join(entries)
                return ToolResult(success=True, data={"type": "directory", "content": content})

            with open(file_path, "r", encoding="utf-8") as f:
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
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, data={"file_path": file_path, "bytes_written": len(content)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class EditTool(SyncTool):
    """Edit a file by replacing old_string with new_string."""

    META = {"category": "file", "max_calls_per_run": 3, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing a specific string with new content."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "old_string": {"type": "string", "description": "Exact string to find and replace"},
                "new_string": {"type": "string", "description": "Replacement string"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences (default False)"}
            },
            "required": ["file_path", "old_string", "new_string"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_string = kwargs.get("old_string")
        new_string = kwargs.get("new_string")
        replace_all = kwargs.get("replace_all", False)

        try:
            if not os.path.exists(file_path):
                return ToolResult(success=False, error=f"File not found: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult(success=False, error=f"String not found in file: {old_string[:50]}...")

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(success=True, data={
                "file_path": file_path,
                "replacements": new_content.count(new_string) if replace_all else 1
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
            matches = glob_module.glob(pattern, root_dir=base_path)
            matches.sort()
            return ToolResult(success=True, data={"matches": matches, "count": len(matches)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
        import re
        pattern = kwargs.get("pattern")
        base_path = kwargs.get("path", ".")
        include = kwargs.get("include")

        try:
            regex = re.compile(pattern)
            results = []

            for root, dirs, files in os.walk(base_path):
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
                    except:
                        continue

            return ToolResult(success=True, data={"results": results, "count": len(results)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
            if not os.path.exists(path):
                return ToolResult(success=False, error=f"Path not found: {path}")

            if not os.path.isdir(path):
                return ToolResult(success=False, error=f"Not a directory: {path}")

            entries = os.listdir(path)
            entries_info = []
            for entry in entries:
                full_path = os.path.join(path, entry)
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