"""
Tool Registry

Central registry for all available tools.
"""

from typing import Dict, List, Optional

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult


class ToolRegistry:
    """
    Registry that holds all available tools.
    Tools are indexed by name for quick lookup.
    """

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_names: List[str] = []

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_default_tools()
        return cls._instance

    def _register_default_tools(self):
        """Register all built-in tools."""
        from app.services.agent_tools.tools.file_tools import (
            ReadTool, WriteTool, EditTool, GlobTool, GrepTool, ListDirTool
        )
        from app.services.agent_tools.tools.system_tools import (
            BashTool, DockerTool, GitTool, PkillTool
        )
        from app.services.agent_tools.tools.web_tools import (
            WebFetchTool, WebSearchTool, APIFetchTool
        )
        from app.services.agent_tools.tools.database_tools import (
            PostgresQueryTool, PostgresListTablesTool, PostgresDescribeTableTool
        )
        from app.services.agent_tools.tools.telegram_tools import (
            TelegramSendMessageTool, TelegramSendNotificationTool,
            TelegramGetUserInfoTool, TelegramBotHealthTool
        )

        tools = [
            ReadTool(),
            WriteTool(),
            EditTool(),
            GlobTool(),
            GrepTool(),
            ListDirTool(),
            BashTool(),
            DockerTool(),
            GitTool(),
            PkillTool(),
            WebFetchTool(),
            WebSearchTool(),
            APIFetchTool(),
            PostgresQueryTool(),
            PostgresListTablesTool(),
            PostgresDescribeTableTool(),
            TelegramSendMessageTool(),
            TelegramSendNotificationTool(),
            TelegramGetUserInfoTool(),
            TelegramBotHealthTool(),
        ]

        for tool in tools:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        self._tool_names.append(tool.name)

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool by name."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            self._tool_names.remove(tool_name)
            return True
        return False

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_all_definitions(self) -> List[Dict]:
        """Get JSON schema definitions for all tools (for LLM function calling)."""
        definitions = []
        for tool in self._tools.values():
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return definitions

    def list_names(self) -> List[str]:
        """List all tool names."""
        return self._tool_names

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            return ToolResult(success=False, error=f"Tool execution failed: {str(e)}")

    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools>"


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return ToolRegistry.get_instance()


def get_tool_definitions() -> List[Dict]:
    """Get all tool definitions for LLM function calling."""
    return get_registry().get_all_definitions()