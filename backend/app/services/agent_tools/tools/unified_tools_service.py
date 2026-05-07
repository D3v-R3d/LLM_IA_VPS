"""
Tools Service

Unified interface for LLM tool calling.
Orchestrates web search, URL fetch, and API calls.
"""

from typing import List, Dict, Any
from app.services.agent_tools.tools.web_search import WebSearchService
from app.services.agent_tools.tools.url_fetch import URLFetchService
from app.services.agent_tools.tools.api_caller import APICallerService
from app.services.synology import SynologyClient, SynologyAuth, FileStation


class ToolsService:
    """
    Unified service for LLM external tool calls.

    Provides a single interface for executing tools
    and defines available tools for function calling.
    """

    def __init__(self):
        """Initialize with sub-services."""
        self.web_search = WebSearchService()
        self.url_fetch = URLFetchService()
        self.api_caller = APICallerService()
        client = SynologyClient()
        auth = SynologyAuth(client)
        auth.login()
        self.nas = FileStation(client)

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions for LLM function calling.

        Returns:
            List of tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Quick web search for facts. Returns titles, URLs and snippets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_url",
                    "description": "Fetch content from a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to fetch"},
                            "max_length": {
                                "type": "integer",
                                "description": "Max characters (default 4000)",
                                "default": 4000
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "call_api",
                    "description": "Call an external API endpoint.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "API endpoint URL"},
                            "method": {
                                "type": "string",
                                "description": "HTTP method",
                                "default": "GET"
                            },
                            "headers": {"type": "object", "description": "HTTP headers"},
                            "body": {"type": "object", "description": "Request body"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_and_fetch",
                    "description": "Search web AND get full content from most relevant page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "nas_list_share",
                    "description": "List all shares on the Synology NAS.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "nas_list_folder",
                    "description": "List contents of a folder on Synology NAS.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_path": {"type": "string", "description": "Folder path on NAS (e.g. /chat or /PlexMediaServer)"}
                        },
                        "required": ["folder_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "nas_search",
                    "description": "Search for files on Synology NAS.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_path": {"type": "string", "description": "Folder path to search in"},
                            "keyword": {"type": "string", "description": "Search keyword"}
                        },
                        "required": ["folder_path", "keyword"]
                    }
                }
            }
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with arguments.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name == "search_web":
            return await self.web_search.search(
                query=arguments.get("query", ""),
                num_results=arguments.get("num_results", 5)
            )
        elif tool_name == "fetch_url":
            return await self.url_fetch.fetch(
                url=arguments.get("url", ""),
                max_length=arguments.get("max_length", 4000)
            )
        elif tool_name == "call_api":
            return await self.api_caller.call(
                url=arguments.get("url", ""),
                method=arguments.get("method", "GET"),
                headers=arguments.get("headers"),
                body=arguments.get("body")
            )
        elif tool_name == "search_and_fetch":
            return await self.web_search.search_and_fetch(
                query=arguments.get("query", "")
            )
        elif tool_name == "nas_list_share":
            return self.nas.list_shares()
        elif tool_name == "nas_list_folder":
            return self.nas.list_folders(folder_path=arguments.get("folder_path", "/"))
        elif tool_name == "nas_search":
            return self.nas.search(folder_path=arguments.get("folder_path", "/"), keyword=arguments.get("keyword", ""))
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

    def format_tools_for_llm(self) -> str:
        """
        Format tools as description string for LLM.

        Returns:
            Human-readable tool descriptions
        """
        tools_desc = []
        for tool in self.get_tools():
            func = tool["function"]
            tools_desc.append(f"- {func['name']}: {func['description']}")
        return "\n".join(tools_desc)