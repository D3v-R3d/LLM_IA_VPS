"""
Permissions

Tool-level permissions and access control.
"""

from typing import Dict, List, Set, Optional


class ToolPermissions:
    """
    Manage tool permissions.
    
    Supports:
    - Global allow/deny lists
    - Per-tool allow/deny
    - Category-based restrictions
    """
    
    def __init__(
        self,
        global_allow: Optional[List[str]] = None,
        global_deny: Optional[List[str]] = None,
        tool_permissions: Optional[Dict[str, Dict[str, List[str]]]] = None,
    ):
        # Global lists: if allow is set, only those tools are allowed.
        # If deny is set, those tools are denied (even if in allow).
        self._global_allow: Set[str] = set(global_allow or [])
        self._global_deny: Set[str] = set(global_deny or [])
        
        # Per-tool permissions: {"tool_name": {"allow": [...], "deny": [...]}}
        self._tool_perms = tool_permissions or {}
    
    def is_allowed(self, tool_name: str, user: Optional[str] = None) -> bool:
        """Check if a tool is allowed."""
        # Check global deny first
        if tool_name in self._global_deny:
            return False
        
        # Check global allow (if set)
        if self._global_allow and tool_name not in self._global_allow:
            return False
        
        # Check per-tool permissions (if any)
        tool_perm = self._tool_perms.get(tool_name)
        if tool_perm:
            deny_list = tool_perm.get("deny", [])
            if user in deny_list or (not user and "all" in deny_list):
                return False
            allow_list = tool_perm.get("allow")
            if allow_list:
                if user in allow_list or (not user and "all" in allow_list):
                    return True
                # If allow list exists but user not in it, deny
                return False
        
        return True
    
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


# Global instance (singleton)
_default_permissions: Optional[ToolPermissions] = None


def get_permissions() -> ToolPermissions:
    """Get global permissions instance."""
    global _default_permissions
    if _default_permissions is None:
        _default_permissions = ToolPermissions()
    return _default_permissions
