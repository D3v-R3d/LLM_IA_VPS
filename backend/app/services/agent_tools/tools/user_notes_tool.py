"""
User Notes Tool - Write notes to user-configured file

Tool for writing notes to a file path configured via user preferences.
Folder: /home/projects/tower_project/prompt (or user preference 'prompt_folder')
File: user's preference 'prompt_filename' or default 'notes.md'
"""

import os
from datetime import datetime
from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


class UserNotesTool(BaseTool):
    """Write notes to user-configured file based on preferences."""

    @property
    def name(self) -> str:
        return "user_write_notes"

    @property
    def description(self) -> str:
        return "Write notes to /home/projects/tower_project/prompt/notes.md"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["content"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        content = kwargs.get("content", "")
        
        file_path = "/home/projects/tower_project/prompt/notes.md"
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            timestamp = datetime.now().isoformat()
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n## Note at {timestamp}\n")
                f.write(content)
                f.write("\n")
            return ToolResult(success=True, data={
                "file_path": file_path,
                "bytes_written": len(content),
                "timestamp": timestamp
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))