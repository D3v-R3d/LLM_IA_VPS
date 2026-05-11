"""
tool_registry/__init__.py

Tool registry module.
"""

from app.services.tool_registry.registry import (
    get_all_tools,
    get_tools_by_category,
    search_tools,
)
from app.services.tool_registry.qdrant_sync import (
    init_tool_registry,
    sync_tools_to_qdrant,
    sync_tools_to_qdrant_sync,
)

__all__ = [
    "get_all_tools",
    "get_tools_by_category",
    "search_tools",
    "init_tool_registry",
    "sync_tools_to_qdrant",
    "sync_tools_to_qdrant_sync",
]


_indexed_count = 0


def get_indexed_count() -> int:
    return _indexed_count


def set_indexed_count(n: int) -> None:
    global _indexed_count
    _indexed_count = n
