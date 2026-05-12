"""
Agent Tools

File tools: read, write, edit, glob, grep, ls
System tools: bash, docker, git, pkill
Web tools: web_fetch, web_search, api_fetch
Database tools: postgres_query_read, postgres_query_write, postgres_list_tables, postgres_describe_table, qdrant_search
Communication tools: telegram_send_message, telegram_send_notification, etc.
NAS tools: nas_list_share, nas_list_folder, nas_search
Scraper tools: scrape_and_store, search_stored_content
Utils tools: user_write_notes
"""

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool

from app.services.agent_tools.tools.file import (
    ReadTool, WriteTool, EditTool, GlobTool, GrepTool, ListDirTool
)
from app.services.agent_tools.tools.system import (
    BashTool, DockerTool, GitTool, PkillTool
)
from app.services.agent_tools.tools.web import (
    WebFetchTool, WebSearchTool, APIFetchTool
)
from app.services.agent_tools.tools.database import (
    PostgresQueryReadTool, PostgresQueryWriteTool,
    PostgresListTablesTool, PostgresDescribeTableTool,
    QdrantSearchTool
)
from app.services.agent_tools.tools.communication import (
    TelegramSendMessageTool, TelegramSendNotificationTool,
    TelegramGetUserInfoTool, TelegramBotHealthTool
)

from app.services.agent_tools.tools.nas import (
    NasListShareTool, NasListFolderTool, NasSearchTool
)
from app.services.agent_tools.tools.scraper import (
    ScrapeAndStoreTool, SearchStoredContentTool
)
from app.services.agent_tools.tools.utils import (
    UserNotesTool
)

try:
    from app.services.agent_tools.tools.model import ModelSwitchTool
except ImportError:
    ModelSwitchTool = None

__all__ = [
    "BaseTool", "ToolResult", "SyncTool",
    "ReadTool", "WriteTool", "EditTool", "GlobTool", "GrepTool", "ListDirTool",
    "BashTool", "DockerTool", "GitTool", "PkillTool",
    "WebFetchTool", "WebSearchTool", "APIFetchTool",
    "PostgresQueryReadTool", "PostgresQueryWriteTool",
    "PostgresListTablesTool", "PostgresDescribeTableTool",
    "QdrantSearchTool",
    "TelegramSendMessageTool", "TelegramSendNotificationTool",
    "TelegramGetUserInfoTool", "TelegramBotHealthTool",
    "NasListShareTool", "NasListFolderTool", "NasSearchTool",
    "ScrapeAndStoreTool", "SearchStoredContentTool",
    "UserNotesTool",
]

if ModelSwitchTool is not None:
    __all__.append("ModelSwitchTool")