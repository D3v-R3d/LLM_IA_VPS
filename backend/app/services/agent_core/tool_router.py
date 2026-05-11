"""
tool_router.py

Deterministic routing layer for tool selection.
Runs BEFORE embeddings for fast-path routing of simple/unambiguous queries.

Returns:
- List[str] of tool names if rule matches
- None if no rule matches (fallback to embeddings)
"""

import re
from typing import List, Optional

ROUTER_RULES = {
    # Math / computation (highest priority - checked first)
    r"\d+\s*[\+\-\*\/]\s*\d+": ["calculator"],
    r"\bcalculate\b": ["calculator"],
    r"\bcompute\b": ["calculator"],
    r"\bcalculer\b": ["calculator"],
    r"\bcalcul\b": ["calculator"],
    r"\bmath\b": ["calculator"],
    
    # Shell / command execution
    r"\brun command\b": ["bash"],
    r"\bexecute\b": ["bash"],
    r"\bbash\b": ["bash"],
    r"\bterminal\b": ["bash"],
    r"\bshell\b": ["bash"],
    r"\bcommande\b": ["bash"],
    r"\blancer\b": ["bash"],
    r"\bexecuter\b": ["bash"],
    
    # File operations (specific verbs before generic "file")
    r"\bedit file\b": ["edit_file"],
    r"\bedit.*fichier\b": ["edit_file"],
    r"\bwrite file\b": ["write_file"],
    r"\becrire.*fichier\b": ["write_file"],
    r"\bopen file\b": ["read_file"],
    r"\bouvrir.*fichier\b": ["read_file"],
    r"\bread file\b": ["read_file"],
    r"\blire.*fichier\b": ["read_file"],
    r"\bmodify file\b": ["edit_file"],
    r"\bmodifier.*fichier\b": ["edit_file"],
    r"\bfichier\b": ["read_file", "write_file", "edit_file"],
    r"\bread\b": ["read_file"],
    r"\bwrite\b": ["write_file"],
    r"\bedit\b": ["edit_file"],
    r"\bmodify\b": ["edit_file"],
    r"\blire\b": ["read_file"],
    r"\becrire\b": ["write_file"],
    r"\bediter\b": ["edit_file"],
    r"\bmodifier\b": ["edit_file"],
    
    # Database operations
    r"\bdescribe table\b": ["postgres_describe_table"],
    r"\blist tables\b": ["postgres_list_tables"],
    r"\blister tables\b": ["postgres_list_tables"],
    r"\btable\b": ["postgres_list_tables", "postgres_describe_table"],
    r"\bsql\b": ["postgres_query_read", "postgres_query_write"],
    r"\bpostgres\b": ["postgres_query_read", "postgres_list_tables"],
    r"\bdatabase\b": ["postgres_query_read", "postgres_list_tables"],
    r"\bbase de donnees\b": ["postgres_query_read"],
    r"\bbase de données\b": ["postgres_query_read"],
    
    # NAS / storage operations
    r"\bnas\b": ["nas_search", "nas_list_share"],
    r"\bsynology\b": ["nas_search"],
    r"\blist folder\b": ["nas_list_folder"],
    r"\bopen folder\b": ["nas_list_folder"],
    r"\bfolder\b": ["nas_list_folder", "nas_find_folder"],
    r"\bdirectory\b": ["nas_list_folder"],
    r"\bdossier\b": ["nas_list_folder", "nas_find_folder"],
    r"\blist files\b": ["nas_search"],
    r"\bpartage\b": ["nas_list_share"],
    r"\bpartages\b": ["nas_list_share"],
    
    # Telegram / external APIs
    r"\btelegram\b": ["telegram_send_message"],
    r"\bsend message\b": ["telegram_send_message"],
    r"\bnotify\b": ["telegram_send_notification"],
    r"\bmessage.*telegram\b": ["telegram_send_message"],
    r"\benvoyer.*telegram\b": ["telegram_send_message"],
    
    # Web search
    r"\bsearch internet\b": ["web_search"],
    r"\bgoogle\b": ["web_search"],
    r"\bweb search\b": ["web_search"],
    r"\brecherche.*internet\b": ["web_search"],
    r"\brechercher.*web\b": ["web_search"],
}


def route(user_message: str) -> Optional[List[str]]:
    """
    Deterministic routing for tool selection.
    
    Args:
        user_message: User's message
        
    Returns:
        List of tool names if rule matches, None otherwise
    """
    msg = user_message.strip().lower()
    
    for pattern, tools in ROUTER_RULES.items():
        if re.search(pattern, msg):
            return tools
    
    return None
