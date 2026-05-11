"""
tool_router.py

Deterministic routing layer for tool selection with ambiguity detection.
Returns structured routing decisions with scope metadata.

Returns ALWAYS Dict:
{
    "tools": List[str],
    "is_ambiguous": bool,
    "scope_candidates": List[str],
    "reason": str
}
"""

import re
from typing import Dict, List, Optional, Set

# ═══════════════════════════════════════════════════════════════════════
# SCOPE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

SCOPES: Dict[str, Set[str]] = {
    "local_fs": {"glob", "ls", "find", "read_file", "grep", "write_file", "edit_file"},
    "nas": {"nas_find_folder", "nas_find_file", "nas_search", "nas_list_folder", "nas_list_share"},
    "vector": {"qdrant_search", "search_stored_content", "scrape_and_store"},
    "postgres": {"postgres_query_read", "postgres_query_write", "postgres_list_tables", "postgres_describe_table"},
    "telegram": {"telegram_send_message", "telegram_send_notification", "telegram_get_user_info", "telegram_bot_health"},
    "web": {"web_search", "web_fetch", "api_call"},
    "docker": {"docker"},
    "system": {"bash", "pkill", "git"},
    "api": {"api_call"},
    "memory": {"user_write_notes"},
    "database": {"postgres_query_read", "postgres_query_write", "postgres_list_tables", "postgres_describe_table"},  # alias
}

# Tool → Scope reverse mapping
TOOL_TO_SCOPE: Dict[str, str] = {}
for scope, tools in SCOPES.items():
    for tool in tools:
        TOOL_TO_SCOPE[tool] = scope

# ═══════════════════════════════════════════════════════════════════════
# SCOPE KEYWORDS (explicit scope detection)
# ═══════════════════════════════════════════════════════════════════════

SCOPE_KEYWORDS: Dict[str, List[str]] = {
    "local_fs": ["local", "filesystem", "disk", "path", "/"],
    "nas": ["nas", "synology", "shared folder", "partage", "network drive"],
    "postgres": ["postgres", "postgresql", "sql", "database", "table"],
    "telegram": ["telegram", "message", "notify", "notification"],
    "web": ["internet", "web", "google", "search engine", "url", "http"],
    "docker": ["docker", "container", "image", "compose"],
    "system": ["bash", "shell", "terminal", "command", "execute"],
    "memory": ["memory", "note", "remember", "save note"],
    "vector": ["vector", "embedding", "semantic", "memory"],
}

# ═══════════════════════════════════════════════════════════════════════
# AMBIGUOUS PATTERNS (generic terms without scope)
# These trigger multi-scope tool expansion
# ═══════════════════════════════════════════════════════════════════════

AMBIGUOUS_PATTERNS: Dict[str, Dict] = {
    # Folder/directory search (no scope specified)
    r"\bdossier\b": {
        "scopes": ["local_fs", "nas", "vector"],
        "tools": ["glob", "nas_find_folder", "qdrant_search"],
        "reason": "generic 'dossier' without scope"
    },
    r"\bfolder\b": {
        "scopes": ["local_fs", "nas", "vector"],
        "tools": ["glob", "nas_find_folder", "qdrant_search"],
        "reason": "generic 'folder' without scope"
    },
    r"\bdirectory\b": {
        "scopes": ["local_fs", "nas"],
        "tools": ["ls", "nas_list_folder"],
        "reason": "generic 'directory' without scope"
    },
    
    # File search (no scope specified)
    r"\bfichier\b": {
        "scopes": ["local_fs", "nas"],
        "tools": ["read_file", "glob", "nas_search"],
        "reason": "generic 'fichier' without scope"
    },
    r"\bfile\b": {
        "scopes": ["local_fs", "nas"],
        "tools": ["read_file", "glob", "nas_search"],
        "reason": "generic 'file' without scope"
    },
    
    # Search operations (no scope specified)
    r"\bsearch\b": {
        "scopes": ["local_fs", "nas", "vector", "web"],
        "tools": ["grep", "nas_search", "qdrant_search", "web_search"],
        "reason": "generic 'search' without scope"
    },
    r"\brecherche\b": {
        "scopes": ["local_fs", "nas", "vector", "web"],
        "tools": ["grep", "nas_search", "qdrant_search", "web_search"],
        "reason": "generic 'recherche' without scope"
    },
    r"\bfind\b": {
        "scopes": ["local_fs", "nas", "vector"],
        "tools": ["glob", "nas_find_file", "qdrant_search"],
        "reason": "generic 'find' without scope"
    },
    r"\btrouve\b": {
        "scopes": ["local_fs", "nas", "vector"],
        "tools": ["glob", "nas_find_file", "qdrant_search"],
        "reason": "generic 'trouve' without scope"
    },
    
    # List operations (no scope specified)
    r"\blist\b": {
        "scopes": ["local_fs", "nas", "postgres"],
        "tools": ["ls", "nas_list_share", "postgres_list_tables"],
        "reason": "generic 'list' without scope"
    },
    r"\blister\b": {
        "scopes": ["local_fs", "nas", "postgres"],
        "tools": ["ls", "nas_list_share", "postgres_list_tables"],
        "reason": "generic 'lister' without scope"
    },
    
    # Read/open operations (no scope specified)
    r"\bouvrir\b": {
        "scopes": ["local_fs"],
        "tools": ["read_file"],
        "reason": "generic 'ouvrir' defaults to local filesystem"
    },
    r"\bopen\b": {
        "scopes": ["local_fs"],
        "tools": ["read_file"],
        "reason": "generic 'open' defaults to local filesystem"
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SPECIFIC PATTERNS (explicit scope mentioned)
# These return single-scope tools (not ambiguous)
# ═══════════════════════════════════════════════════════════════════════

SPECIFIC_PATTERNS: Dict[str, Dict] = {
    # Math / computation (highest priority - checked first)
    r"\d+\s*[\+\-\*\/]\s*\d+": {
        "scopes": ["system"],
        "tools": ["calculator"],
        "reason": "mathematical expression"
    },
    r"\bcalculate\b": {"scopes": ["system"], "tools": ["calculator"], "reason": "calculation request"},
    r"\bcompute\b": {"scopes": ["system"], "tools": ["calculator"], "reason": "computation request"},
    r"\bcalculer\b": {"scopes": ["system"], "tools": ["calculator"], "reason": "calculation request"},
    r"\bcalcul\b": {"scopes": ["system"], "tools": ["calculator"], "reason": "calculation request"},
    
    # NAS-specific (explicit scope)
    r"\bdossier.*nas\b": {"scopes": ["nas"], "tools": ["nas_find_folder"], "reason": "NAS folder search"},
    r"\bnas.*dossier\b": {"scopes": ["nas"], "tools": ["nas_find_folder"], "reason": "NAS folder search"},
    r"\bfolder.*nas\b": {"scopes": ["nas"], "tools": ["nas_find_folder"], "reason": "NAS folder search"},
    r"\bnas.*folder\b": {"scopes": ["nas"], "tools": ["nas_find_folder"], "reason": "NAS folder search"},
    r"\bfichier.*nas\b": {"scopes": ["nas"], "tools": ["nas_search"], "reason": "NAS file search"},
    r"\bnas.*fichier\b": {"scopes": ["nas"], "tools": ["nas_search"], "reason": "NAS file search"},
    r"\bfile.*nas\b": {"scopes": ["nas"], "tools": ["nas_search"], "reason": "NAS file search"},
    r"\bnas.*file\b": {"scopes": ["nas"], "tools": ["nas_search"], "reason": "NAS file search"},
    r"\bsynology\b": {"scopes": ["nas"], "tools": ["nas_search"], "reason": "Synology NAS operation"},
    r"\bpartage\b": {"scopes": ["nas"], "tools": ["nas_list_share"], "reason": "NAS shared folder"},
    r"\bpartages\b": {"scopes": ["nas"], "tools": ["nas_list_share"], "reason": "NAS shared folders"},
    
    # Shell / command execution (explicit scope)
    r"\brun command\b": {"scopes": ["system"], "tools": ["bash"], "reason": "shell command execution"},
    r"\bexecute\b": {"scopes": ["system"], "tools": ["bash"], "reason": "command execution"},
    r"\bbash\b": {"scopes": ["system"], "tools": ["bash"], "reason": "bash shell"},
    r"\bterminal\b": {"scopes": ["system"], "tools": ["bash"], "reason": "terminal command"},
    r"\bshell\b": {"scopes": ["system"], "tools": ["bash"], "reason": "shell command"},
    r"\bcommande\b": {"scopes": ["system"], "tools": ["bash"], "reason": "command execution"},
    r"\blancer\b": {"scopes": ["system"], "tools": ["bash"], "reason": "launch command"},
    r"\bexecuter\b": {"scopes": ["system"], "tools": ["bash"], "reason": "execute command"},
    
    # Database-specific (explicit scope)
    r"\bdescribe table\b": {"scopes": ["postgres"], "tools": ["postgres_describe_table"], "reason": "Postgres table description"},
    r"\blist tables\b": {"scopes": ["postgres"], "tools": ["postgres_list_tables"], "reason": "Postgres table listing"},
    r"\blister tables\b": {"scopes": ["postgres"], "tools": ["postgres_list_tables"], "reason": "Postgres table listing"},
    r"\btable\b": {"scopes": ["postgres"], "tools": ["postgres_list_tables", "postgres_describe_table"], "reason": "database table operation"},
    r"\bsql\b": {"scopes": ["postgres"], "tools": ["postgres_query_read", "postgres_query_write"], "reason": "SQL query"},
    r"\bpostgres\b": {"scopes": ["postgres"], "tools": ["postgres_query_read", "postgres_list_tables"], "reason": "PostgreSQL operation"},
    r"\bdatabase\b": {"scopes": ["postgres"], "tools": ["postgres_query_read", "postgres_list_tables"], "reason": "database operation"},
    r"\bbase de donnees\b": {"scopes": ["postgres"], "tools": ["postgres_query_read"], "reason": "database operation"},
    r"\bbase de données\b": {"scopes": ["postgres"], "tools": ["postgres_query_read"], "reason": "database operation"},
    
    # Telegram-specific (explicit scope)
    r"\btelegram\b": {"scopes": ["telegram"], "tools": ["telegram_send_message"], "reason": "Telegram operation"},
    r"\bsend message\b": {"scopes": ["telegram"], "tools": ["telegram_send_message"], "reason": "message sending"},
    r"\bnotify\b": {"scopes": ["telegram"], "tools": ["telegram_send_notification"], "reason": "notification"},
    r"\benvoyer.*telegram\b": {"scopes": ["telegram"], "tools": ["telegram_send_message"], "reason": "Telegram message"},
    
    # Web-specific (explicit scope)
    r"\bsearch internet\b": {"scopes": ["web"], "tools": ["web_search"], "reason": "internet search"},
    r"\bgoogle\b": {"scopes": ["web"], "tools": ["web_search"], "reason": "Google search"},
    r"\bweb search\b": {"scopes": ["web"], "tools": ["web_search"], "reason": "web search"},
    r"\brecherche.*internet\b": {"scopes": ["web"], "tools": ["web_search"], "reason": "internet search"},
    r"\brechercher.*web\b": {"scopes": ["web"], "tools": ["web_search"], "reason": "web search"},
    
    # Docker-specific (explicit scope)
    r"\bdocker\b": {"scopes": ["docker"], "tools": ["docker"], "reason": "Docker operation"},
    
    # File operations with specific verbs (single tool)
    r"\bedit file\b": {"scopes": ["local_fs"], "tools": ["edit_file"], "reason": "file editing"},
    r"\bedit.*fichier\b": {"scopes": ["local_fs"], "tools": ["edit_file"], "reason": "file editing"},
    r"\bwrite file\b": {"scopes": ["local_fs"], "tools": ["write_file"], "reason": "file writing"},
    r"\becrire.*fichier\b": {"scopes": ["local_fs"], "tools": ["write_file"], "reason": "file writing"},
    r"\bread file\b": {"scopes": ["local_fs"], "tools": ["read_file"], "reason": "file reading"},
    r"\blire.*fichier\b": {"scopes": ["local_fs"], "tools": ["read_file"], "reason": "file reading"},
    r"\bmodify file\b": {"scopes": ["local_fs"], "tools": ["edit_file"], "reason": "file modification"},
    r"\bmodifier.*fichier\b": {"scopes": ["local_fs"], "tools": ["edit_file"], "reason": "file modification"},
}


def _has_explicit_scope(msg: str) -> Optional[str]:
    """
    Detect if message contains explicit scope keywords.
    Returns scope name if found, None otherwise.
    """
    msg_lower = msg.lower()
    for scope, keywords in SCOPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in msg_lower:
                return scope
    return None


def route(user_message: str) -> Dict:
    """
    Deterministic routing for tool selection with ambiguity detection.
    
    Args:
        user_message: User's message
        
    Returns:
        Dict with structure:
        {
            "tools": List[str],
            "is_ambiguous": bool,
            "scope_candidates": List[str],
            "reason": str
        }
    """
    msg = user_message.strip().lower()
    
    # Step 1: Check specific patterns first (explicit scope = not ambiguous)
    for pattern, config in SPECIFIC_PATTERNS.items():
        if re.search(pattern, msg):
            return {
                "tools": config["tools"][:2],  # Limit to 2 tools max for specific
                "is_ambiguous": False,
                "scope_candidates": config["scopes"],
                "reason": config["reason"]
            }
    
    # Step 2: Check ambiguous patterns (no explicit scope)
    for pattern, config in AMBIGUOUS_PATTERNS.items():
        if re.search(pattern, msg):
            # Check if there's an explicit scope that would make this non-ambiguous
            explicit_scope = _has_explicit_scope(msg)
            if explicit_scope:
                # User mentioned a scope → filter tools to that scope only
                scope_tools = [t for t in config["tools"] if TOOL_TO_SCOPE.get(t) == explicit_scope]
                if scope_tools:
                    return {
                        "tools": scope_tools,
                        "is_ambiguous": False,
                        "scope_candidates": [explicit_scope],
                        "reason": f"{config['reason']} (scoped to {explicit_scope})"
                    }
            
            # No explicit scope → return multi-scope tools (ambiguous)
            return {
                "tools": config["tools"][:5],  # Limit to 3-5 tools for ambiguous
                "is_ambiguous": True,
                "scope_candidates": config["scopes"],
                "reason": config["reason"]
            }
    
    # Step 3: No pattern matched → fallback to embeddings (return None indicator)
    return {
        "tools": [],
        "is_ambiguous": False,
        "scope_candidates": [],
        "reason": "no pattern matched, fallback to embeddings"
    }


def get_tool_scope(tool_name: str) -> Optional[str]:
    """Get the scope for a given tool name."""
    return TOOL_TO_SCOPE.get(tool_name)
