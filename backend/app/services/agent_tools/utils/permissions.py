"""
Permissions

Tool-level permissions and access control.

Permission levels:
- "read": Read operations (read_file, glob, ls, search)
- "write": Write operations (write_file, edit_file)
- "delete": Delete operations (not implemented yet)
- "execute": Execute operations (bash, docker)

Default behavior:
- Read: allowed for all users
- Write/Delete: requires Telegram confirmation
"""

from typing import Dict, List, Set, Optional
from enum import Enum


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


# Tool → Permission Level mapping
TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
    # READ operations (default: allowed)
    "read_file": PermissionLevel.READ,
    "glob": PermissionLevel.READ,
    "ls": PermissionLevel.READ,
    "grep": PermissionLevel.READ,
    "nas_search": PermissionLevel.READ,
    "nas_find_folder": PermissionLevel.READ,
    "nas_find_file": PermissionLevel.READ,
    "nas_list_folder": PermissionLevel.READ,
    "nas_list_share": PermissionLevel.READ,
    "postgres_query_read": PermissionLevel.READ,
    "postgres_list_tables": PermissionLevel.READ,
    "postgres_describe_table": PermissionLevel.READ,
    "qdrant_search": PermissionLevel.READ,
    "search_stored_content": PermissionLevel.READ,
    "web_search": PermissionLevel.READ,
    "web_fetch": PermissionLevel.READ,
    "api_call": PermissionLevel.READ,
    "telegram_get_user_info": PermissionLevel.READ,
    "telegram_bot_health": PermissionLevel.READ,
    
    # WRITE operations (requires confirmation)
    "write_file": PermissionLevel.WRITE,
    "edit_file": PermissionLevel.WRITE,
    "postgres_query_write": PermissionLevel.WRITE,
    "user_write_notes": PermissionLevel.WRITE,
    "telegram_send_message": PermissionLevel.WRITE,
    "telegram_send_notification": PermissionLevel.WRITE,
    "scrape_and_store": PermissionLevel.WRITE,
    
    # EXECUTE operations (requires confirmation)
    "bash": PermissionLevel.EXECUTE,
    "docker": PermissionLevel.EXECUTE,
    "git": PermissionLevel.EXECUTE,
    "pkill": PermissionLevel.EXECUTE,
}

TOOL_CATEGORIES = {
    "read": {
        "read_file", "glob", "ls", "grep",
        "nas_search", "nas_find_folder", "nas_find_file",
        "nas_list_folder", "nas_list_share",
        "postgres_query_read", "postgres_list_tables", "postgres_describe_table",
        "qdrant_search", "search_stored_content",
    },
    "write": {
        "write_file", "edit_file", "postgres_query_write", "user_write_notes",
    },
    "execute": {
        "bash", "docker", "git", "pkill",
    },
}


class ToolPermissions:
    """
    Manage tool permissions.
    
    Supports:
    - Global allow/deny lists
    - Per-tool permissions based on permission level
    - Telegram confirmation for write/execute operations
    """
    
    def __init__(
        self,
        global_allow: Optional[List[str]] = None,
        global_deny: Optional[List[str]] = None,
        require_confirmation_for: Optional[List[PermissionLevel]] = None,
    ):
        # Global lists: if allow is set, only those tools are allowed.
        # If deny is set, those tools are denied (even if in allow).
        self._global_allow: Set[str] = set(global_allow or [])
        self._global_deny: Set[str] = set(global_deny or [])
        
        # Permission levels requiring Telegram confirmation
        self._require_confirmation: Set[PermissionLevel] = set(
            require_confirmation_for or [PermissionLevel.DELETE]
        )
    
    def get_permission_level(self, tool_name: str) -> PermissionLevel:
        """Get the permission level for a tool."""
        return TOOL_PERMISSIONS.get(tool_name, PermissionLevel.READ)
    
    def is_allowed(self, tool_name: str, user: Optional[str] = None) -> bool:
        """Check if a tool is allowed (basic check, doesn't handle confirmation)."""
        # Check global deny first
        if tool_name in self._global_deny:
            return False
        
        # Check global allow (if set)
        if self._global_allow and tool_name not in self._global_allow:
            return False
        
        return True
    
    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if a tool requires Telegram confirmation."""
        level = self.get_permission_level(tool_name)
        return level in self._require_confirmation
    
    def get_confirmation_message(self, tool_name: str, arguments: Dict) -> str:
        """Generate Telegram confirmation message for a tool."""
        level = self.get_permission_level(tool_name)
        
        if level == PermissionLevel.WRITE:
            return f"⚠️ Write operation requested\n\nTool: {tool_name}\nArgs: {arguments}\n\nAllow this write operation?"
        elif level == PermissionLevel.EXECUTE:
            return f"⚠️ Execute operation requested\n\nTool: {tool_name}\nArgs: {arguments}\n\nAllow this execution?"
        elif level == PermissionLevel.DELETE:
            return f"⚠️ Delete operation requested\n\nTool: {tool_name}\nArgs: {arguments}\n\nAllow this deletion?"
        
        return f"Confirm: {tool_name}"
    
    def add_to_deny(self, tool_name: str):
        """Add a tool to global deny list."""
        self._global_deny.add(tool_name)
    
    def remove_from_deny(self, tool_name: str):
        """Remove a tool from global deny list."""
        self._global_deny.discard(tool_name)
    
    def add_to_allow(self, tool_name: str):
        """Add a tool to global allow list."""
        self._global_allow.add(tool_name)
    
    def remove_from_allow(self, tool_name: str):
        """Remove a tool from global allow list."""
        self._global_allow.discard(tool_name)

    def allow_category(self, category: str):
        """Allow all tools in a category."""
        tools = TOOL_CATEGORIES.get(category, [])
        for t in tools:
            self._global_allow.add(t)


# Global instance (singleton)
_default_permissions: Optional[ToolPermissions] = None


def get_permissions() -> ToolPermissions:
    """Get global permissions instance."""
    global _default_permissions
    if _default_permissions is None:
        _default_permissions = ToolPermissions()
    return _default_permissions


def reset_permissions():
    """Reset global permissions instance (for testing)."""
    global _default_permissions
    _default_permissions = None
