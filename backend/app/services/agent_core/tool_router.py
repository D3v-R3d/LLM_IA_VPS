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
    # FIX: "database" alias removed — it caused TOOL_TO_SCOPE to overwrite "postgres"
    # entries unpredictably depending on dict iteration order. Use "postgres" everywhere.
}

# Tool → Scope reverse mapping
# FIX: build after removing the alias so each tool maps to exactly one scope.
TOOL_TO_SCOPE: Dict[str, str] = {}
for _scope, _tools in SCOPES.items():
    for _tool in _tools:
        TOOL_TO_SCOPE[_tool] = _scope

# FIX: explicit alias mapping so _has_explicit_scope("database") still resolves correctly
# without polluting TOOL_TO_SCOPE.
SCOPE_ALIAS: Dict[str, str] = {
    "database": "postgres",
}

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
# SPECIFIC PATTERNS (explicit scope mentioned)
# These return single-scope tools (not ambiguous).
# Evaluated BEFORE ambiguous patterns — most specific first.
# ═══════════════════════════════════════════════════════════════════════

# IMPORTANT: ordering matters inside this list. Use a list of tuples so that
# more specific patterns are always checked before broader ones.
# (Python dicts preserve insertion order since 3.7, but a list of tuples
# makes the intent explicit and avoids accidental key collisions.)

SPECIFIC_PATTERNS: List[tuple] = [
    # Math / computation (highest priority)
    (r"\d+\s*[\+\-\*\/]\s*\d+",    {"scopes": ["system"],    "tools": ["calculator"],                                      "reason": "mathematical expression"}),
    (r"\bcalculate\b",              {"scopes": ["system"],    "tools": ["calculator"],                                      "reason": "calculation request"}),
    (r"\bcompute\b",                {"scopes": ["system"],    "tools": ["calculator"],                                      "reason": "computation request"}),
    (r"\bcalculer\b",               {"scopes": ["system"],    "tools": ["calculator"],                                      "reason": "calculation request"}),
    (r"\bcalcul\b",                 {"scopes": ["system"],    "tools": ["calculator"],                                      "reason": "calculation request"}),

    # Vector / semantic search (explicit — before generic "search")
    (r"\bvector\b",                 {"scopes": ["vector"],    "tools": ["qdrant_search"],                                   "reason": "vector search"}),
    (r"\bembedding\b",              {"scopes": ["vector"],    "tools": ["qdrant_search"],                                   "reason": "embedding search"}),
    (r"\bsemantique\b",             {"scopes": ["vector"],    "tools": ["qdrant_search"],                                   "reason": "semantic search"}),
    (r"\bsemantic search\b",        {"scopes": ["vector"],    "tools": ["qdrant_search"],                                   "reason": "semantic search"}),
    (r"\brecherche.*semantique\b",  {"scopes": ["vector"],    "tools": ["qdrant_search"],                                   "reason": "semantic search"}),
    (r"\bnotes.*vectori",           {"scopes": ["vector"],    "tools": ["qdrant_search", "search_stored_content"],          "reason": "vector notes search"}),

    # NAS-specific (explicit scope)
    (r"\bdossier.*nas\b",           {"scopes": ["nas"],       "tools": ["nas_find_folder"],                                 "reason": "NAS folder search"}),
    (r"\bnas.*dossier\b",           {"scopes": ["nas"],       "tools": ["nas_find_folder"],                                 "reason": "NAS folder search"}),
    (r"\bfolder.*nas\b",            {"scopes": ["nas"],       "tools": ["nas_find_folder"],                                 "reason": "NAS folder search"}),
    (r"\bnas.*folder\b",            {"scopes": ["nas"],       "tools": ["nas_find_folder"],                                 "reason": "NAS folder search"}),
    (r"\bfichier.*nas\b",           {"scopes": ["nas"],       "tools": ["nas_search"],                                      "reason": "NAS file search"}),
    (r"\bnas.*fichier\b",           {"scopes": ["nas"],       "tools": ["nas_search"],                                      "reason": "NAS file search"}),
    (r"\bfile.*nas\b",              {"scopes": ["nas"],       "tools": ["nas_search"],                                      "reason": "NAS file search"}),
    (r"\bnas.*file\b",              {"scopes": ["nas"],       "tools": ["nas_search"],                                      "reason": "NAS file search"}),
    (r"\bsynology\b",               {"scopes": ["nas"],       "tools": ["nas_search"],                                      "reason": "Synology NAS operation"}),
    (r"\bpartages?\b",              {"scopes": ["nas"],       "tools": ["nas_list_share"],                                  "reason": "NAS shared folders"}),

    # Database-specific (explicit scope — BEFORE generic \bexecute\b)
    (r"\bdescribe table\b",         {"scopes": ["postgres"],  "tools": ["postgres_describe_table"],                         "reason": "Postgres table description"}),
    (r"\blist tables\b",            {"scopes": ["postgres"],  "tools": ["postgres_list_tables"],                            "reason": "Postgres table listing"}),
    (r"\blister tables\b",          {"scopes": ["postgres"],  "tools": ["postgres_list_tables"],                            "reason": "Postgres table listing"}),
    # FIX: \btable\b removed from SPECIFIC — too broad, collided with NAS/FS patterns.
    # It now lives in AMBIGUOUS_PATTERNS so scope keywords can disambiguate it.
    (r"\bsql\b",                    {"scopes": ["postgres"],  "tools": ["postgres_query_read", "postgres_query_write"],     "reason": "SQL query"}),
    (r"\bpostgres\b",               {"scopes": ["postgres"],  "tools": ["postgres_query_read", "postgres_list_tables"],    "reason": "PostgreSQL operation"}),
    (r"\bpostgresql\b",             {"scopes": ["postgres"],  "tools": ["postgres_query_read", "postgres_list_tables"],    "reason": "PostgreSQL operation"}),
    (r"\bbase de donn[eé]es\b",     {"scopes": ["postgres"],  "tools": ["postgres_query_read"],                            "reason": "database operation"}),

    # Shell / command execution (explicit — AFTER database patterns so
    # "execute a SQL query" doesn't route to bash)
    (r"\brun command\b",            {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "shell command execution"}),
    (r"\bbash\b",                   {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "bash shell"}),
    (r"\bterminal\b",               {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "terminal command"}),
    (r"\bshell\b",                  {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "shell command"}),
    (r"\bcommande\b",               {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "command execution"}),
    (r"\blancer\b",                 {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "launch command"}),
    (r"\bexecuter\b",               {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "execute command"}),
    # FIX: \bexecute\b moved AFTER database patterns and made more specific
    (r"\bexecute\s+(?!sql|query|request)",
                                    {"scopes": ["system"],    "tools": ["bash"],                                            "reason": "command execution"}),

    # Telegram-specific (explicit scope)
    (r"\btelegram\b",               {"scopes": ["telegram"],  "tools": ["telegram_send_message"],                          "reason": "Telegram operation"}),
    (r"\bsend message\b",           {"scopes": ["telegram"],  "tools": ["telegram_send_message"],                          "reason": "message sending"}),
    (r"\bnotify\b",                 {"scopes": ["telegram"],  "tools": ["telegram_send_notification"],                     "reason": "notification"}),
    (r"\benvoyer.*telegram\b",      {"scopes": ["telegram"],  "tools": ["telegram_send_message"],                          "reason": "Telegram message"}),

    # Web-specific (explicit scope)
    (r"\bsearch internet\b",        {"scopes": ["web"],       "tools": ["web_search"],                                     "reason": "internet search"}),
    (r"\bgoogle\b",                 {"scopes": ["web"],       "tools": ["web_search"],                                     "reason": "Google search"}),
    (r"\bweb search\b",             {"scopes": ["web"],       "tools": ["web_search"],                                     "reason": "web search"}),
    (r"\brecherche.*internet\b",    {"scopes": ["web"],       "tools": ["web_search"],                                     "reason": "internet search"}),
    (r"\brechercher.*web\b",        {"scopes": ["web"],       "tools": ["web_search"],                                     "reason": "web search"}),

    # Docker-specific (explicit scope)
    (r"\bdocker\b",                 {"scopes": ["docker"],    "tools": ["docker"],                                         "reason": "Docker operation"}),

    # File operations with specific verbs (single tool)
    (r"\bedit file\b",              {"scopes": ["local_fs"],  "tools": ["edit_file"],                                      "reason": "file editing"}),
    (r"\bedit.*fichier\b",          {"scopes": ["local_fs"],  "tools": ["edit_file"],                                      "reason": "file editing"}),
    (r"\bwrite file\b",             {"scopes": ["local_fs"],  "tools": ["write_file"],                                     "reason": "file writing"}),
    (r"\becrire.*fichier\b",        {"scopes": ["local_fs"],  "tools": ["write_file"],                                     "reason": "file writing"}),
    (r"\bread file\b",              {"scopes": ["local_fs"],  "tools": ["read_file"],                                      "reason": "file reading"}),
    (r"\blire.*fichier\b",          {"scopes": ["local_fs"],  "tools": ["read_file"],                                      "reason": "file reading"}),
    (r"\bmodify file\b",            {"scopes": ["local_fs"],  "tools": ["edit_file"],                                      "reason": "file modification"}),
    (r"\bmodifier.*fichier\b",      {"scopes": ["local_fs"],  "tools": ["edit_file"],                                      "reason": "file modification"}),

    # FIX: \bopen\b removed — too broad ("open source", "open connection"…).
    # Replaced by the more specific verb+noun combos above.
    # \bouvrir\b kept but moved to ambiguous since it also applies to NAS shares.
]

# ═══════════════════════════════════════════════════════════════════════
# AMBIGUOUS PATTERNS (generic terms without scope)
# These trigger multi-scope tool expansion.
# FIX: converted to list of tuples to prevent silent key collisions.
# Order matters: more specific patterns BEFORE generic ones.
# ═══════════════════════════════════════════════════════════════════════

AMBIGUOUS_PATTERNS: List[tuple] = [
    # Photo/image + folder combinations — MORE SPECIFIC, must come first
    (r"\bphoto.*dossier\b",  {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "photo in folder search"}),
    (r"\bdossier.*photo\b",  {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "folder with photo search"}),
    (r"\bimage.*dossier\b",  {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "image in folder search"}),
    (r"\bdossier.*image\b",  {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "folder with image search"}),

    # Photo/image/picture standalone — AFTER combined patterns
    (r"\bphoto\b",           {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "photo/image search without scope"}),
    (r"\bimage\b",           {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "image search without scope"}),
    (r"\bpicture\b",         {"scopes": ["local_fs", "nas"], "tools": ["glob", "grep", "nas_search"],                       "reason": "picture search without scope"}),

    # Folder/directory search (no scope specified)
    (r"\bdossier\b",         {"scopes": ["local_fs", "nas", "vector"], "tools": ["glob", "grep", "nas_find_folder", "qdrant_search"], "reason": "generic 'dossier' without scope"}),
    (r"\bfolder\b",          {"scopes": ["local_fs", "nas", "vector"], "tools": ["glob", "grep", "nas_find_folder", "qdrant_search"], "reason": "generic 'folder' without scope"}),
    (r"\bdirectory\b",       {"scopes": ["local_fs", "nas"],           "tools": ["ls", "nas_list_folder"],                  "reason": "generic 'directory' without scope"}),

    # File search (no scope specified)
    (r"\bfichier\b",         {"scopes": ["local_fs", "nas"], "tools": ["read_file", "glob", "grep", "nas_search"],          "reason": "generic 'fichier' without scope"}),
    (r"\bfile\b",            {"scopes": ["local_fs", "nas"], "tools": ["read_file", "glob", "grep", "nas_search"],          "reason": "generic 'file' without scope"}),

    # Table (ambiguous: could be postgres or something else)
    # FIX: moved here from SPECIFIC so scope keywords can resolve it
    (r"\btable\b",           {"scopes": ["postgres"],        "tools": ["postgres_list_tables", "postgres_describe_table"],  "reason": "database table — confirm scope"}),

    # Search / find operations (no scope specified)
    (r"\bsearch\b",          {"scopes": ["local_fs", "nas", "vector", "web"], "tools": ["grep", "nas_search", "qdrant_search", "web_search"], "reason": "generic 'search' without scope"}),
    (r"\brecherche\b",       {"scopes": ["local_fs", "nas", "vector", "web"], "tools": ["grep", "nas_search", "qdrant_search", "web_search"], "reason": "generic 'recherche' without scope"}),
    (r"\bfind\b",            {"scopes": ["local_fs", "nas", "vector"],        "tools": ["glob", "grep", "nas_find_file", "qdrant_search"],    "reason": "generic 'find' without scope"}),
    (r"\btrouve\b",          {"scopes": ["local_fs", "nas", "vector"],        "tools": ["glob", "grep", "nas_find_file", "qdrant_search"],    "reason": "generic 'trouve' without scope"}),

    # List operations (no scope specified)
    (r"\blist\b",            {"scopes": ["local_fs", "nas", "postgres"], "tools": ["ls", "nas_list_share", "postgres_list_tables"], "reason": "generic 'list' without scope"}),
    (r"\blister\b",          {"scopes": ["local_fs", "nas", "postgres"], "tools": ["ls", "nas_list_share", "postgres_list_tables"], "reason": "generic 'lister' without scope"}),

    # Read/open operations (no scope specified)
    # FIX: \bouvrir\b moved here (was SPECIFIC → local_fs only, but NAS shares can also be "opened")
    (r"\bouvrir\b",          {"scopes": ["local_fs", "nas"], "tools": ["read_file", "nas_list_folder"],                     "reason": "generic 'ouvrir' without scope"}),
    (r"\bopen\b",            {"scopes": ["local_fs"],        "tools": ["read_file"],                                        "reason": "generic 'open' defaults to local filesystem"}),

    # Database generic (no explicit engine keyword)
    (r"\bdatabase\b",        {"scopes": ["postgres"],        "tools": ["postgres_query_read", "postgres_list_tables"],      "reason": "generic 'database' without engine"}),
    (r"\bexecute\b",         {"scopes": ["postgres", "system"], "tools": ["postgres_query_read", "bash"],                   "reason": "ambiguous 'execute' — SQL or shell?"}),
]


def _resolve_scope_alias(scope: str) -> str:
    """Resolve scope alias to canonical scope name."""
    return SCOPE_ALIAS.get(scope, scope)


def _has_explicit_scopes(msg: str) -> List[str]:
    """
    Detect all explicit scope keywords in the message.
    FIX: returns a LIST of scopes instead of just the first one,
    so multi-scope messages ("NAS and postgres") are handled correctly.
    """
    msg_lower = msg.lower()
    found = []
    for scope, keywords in SCOPE_KEYWORDS.items():
        canonical = _resolve_scope_alias(scope)
        for keyword in keywords:
            if keyword in msg_lower:
                if canonical not in found:
                    found.append(canonical)
                break
    return found


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
    for pattern, config in SPECIFIC_PATTERNS:
        if re.search(pattern, msg):
            return {
                "tools": config["tools"],   # FIX: no artificial [:2] cap — trust the pattern definition
                "is_ambiguous": False,
                "scope_candidates": config["scopes"],
                "reason": config["reason"]
            }

    # Step 2: Check ambiguous patterns (no explicit scope declared in the pattern)
    for pattern, config in AMBIGUOUS_PATTERNS:
        if re.search(pattern, msg):
            # Check if the message itself contains explicit scope keywords
            explicit_scopes = _has_explicit_scopes(msg)
            if explicit_scopes:
                # Filter tools to only those belonging to the detected explicit scopes
                scope_tools = [
                    t for t in config["tools"]
                    if _resolve_scope_alias(TOOL_TO_SCOPE.get(t, "")) in explicit_scopes
                ]
                if scope_tools:
                    return {
                        "tools": scope_tools,
                        "is_ambiguous": False,
                        "scope_candidates": explicit_scopes,
                        "reason": f"{config['reason']} (scoped to {', '.join(explicit_scopes)})"
                    }

            # No explicit scope → return multi-scope tools (ambiguous)
            return {
                "tools": config["tools"][:5],
                "is_ambiguous": len(config["scopes"]) > 1,
                "scope_candidates": config["scopes"],
                "reason": config["reason"]
            }

    # Step 3: No pattern matched → fallback to embeddings
    return {
        "tools": [],
        "is_ambiguous": False,
        "scope_candidates": [],
        "reason": "no pattern matched, fallback to embeddings"
    }


def get_tool_scope(tool_name: str) -> Optional[str]:
    """Get the canonical scope for a given tool name."""
    return TOOL_TO_SCOPE.get(tool_name)