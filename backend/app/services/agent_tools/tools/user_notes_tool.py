"""
User Notes Tool - Write notes to the prompt inject folder

Always writes to {PROMPT_DIR}/inject/notes.md
"""

import os
from datetime import datetime
from app.core.config import settings
from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


class UserNotesTool(BaseTool):
    """Write notes to user-configured file based on preferences."""

    @property
    def name(self) -> str:
        return "user_write_notes"

    @property
    def description(self) -> str:
        return "Write notes to notes.md in the prompt inject folder"

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

        file_path = os.path.join(settings.PROMPT_DIR, "inject", "notes.md")

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