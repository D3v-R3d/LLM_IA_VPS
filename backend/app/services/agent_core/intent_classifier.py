"""
Intent Classifier

Keyword-based intent classification for tool routing.
No LLM calls needed — fast, deterministic, lightweight.
"""

from typing import List, Dict, Set

INTENT_PATTERNS: Dict[str, List[str]] = {
    "file_operation": [
        "read", "write", "edit", "file", "glob", "grep", "ls",
        "list", "directory", "folder", "create file", "modify",
        "delete file", "rename", "move", "copy",
        "fichier", "dossier", "lire", "ecrire", "editer",
        "contenu du", "liste les", "affiche",
    ],
    "web_search": [
        "search", "find", "look up", "google", "what is",
        "who is", "latest", "news", "tell me about",
        "information about", "research",
        "cherche", "recherche", "trouve", "internet",
        "web", "information sur", "va voir",
        "quel est", "qui est", "actualite",
        "meme", "image", "photo", "picture", "gif",
    ],
    "web_fetch": [
        "fetch", "scrape", "get content", "extract",
        "download page", "open url", "visit",
        "va sur", "ouvre", "url",
    ],
    "code_execution": [
        "run", "execute", "bash", "command", "terminal",
        "script", "shell",
        "execute", "commande", "terminal",
    ],
    "docker": [
        "docker", "container", "image", "compose",
        "conteneur",
    ],
    "git": [
        "git", "commit", "push", "pull", "branch", "merge",
        "repo", "repository",
    ],
    "database": [
        "query", "sql", "postgres", "database", "db", "table",
        "select", "insert", "update", "delete from",
        "requete", "base de donnees", "bdd", "base de données",
        "postgres", "utilisateurs", "users", "table", "tables",
        "select", "insert", "update", "delete",
    ],
    "nas": [
        "nas", "synology", "share", "drive", "file station",
        "network drive", "storage",
        "partage",
    ],
    "telegram": [
        "send message", "notify", "broadcast", "telegram",
        "send notification",
    ],
    "note_taking": [
        "remember", "note", "save", "write note",
        "take note", "store this",
        "souviens", "note", "retenir", "sauvegarde",
    ],
    "search_stored": [
        "search stored", "find in my", "remember about",
        "what did i save", "search content",
        "cherche dans", "recherche dans", "trouve dans",
        "parmi mes", "dans mes notes",
    ],
    "conversation": [
        "hello", "hi", "hey", "bonjour", "salut",
        "help", "who are you", "what can you",
        "how are you", "thanks", "merci",
        "ca va", "qui es tu", "peux tu",
    ],
}

ALWAYS_INCLUDE: Set[str] = {
    "web_search",
    "model_switch",
    "user_write_notes",
}

INTENT_TO_TOOLS: Dict[str, Set[str]] = {
    "file_operation": {"read_file", "write_file", "edit_file", "glob", "grep", "ls"},
    "web_search": {"web_search", "web_fetch"},
    "web_fetch": {"web_fetch", "scrape_and_store", "search_stored_content"},
    "code_execution": {"bash", "git", "docker"},
    "docker": {"docker"},
    "git": {"git"},
    "database": {"postgres_query", "postgres_list_tables", "postgres_describe_table"},
    "nas": {"nas_list_share", "nas_list_folder", "nas_search"},
    "telegram": {"telegram_send_message", "telegram_send_notification",
                 "telegram_get_user_info", "telegram_bot_health"},
    "note_taking": {"user_write_notes"},
    "search_stored": {"search_stored_content", "qdrant_search", "qdrant_scroll"},
    "conversation": set(),
}


def classify_intent(user_message: str) -> List[str]:
    """Classify user intent based on keyword matching.

    Returns list of matched intent names, ordered by match confidence.
    Always includes 'conversation' as fallback.
    """
    msg_lower = user_message.lower()
    matched: List[str] = []
    scores: Dict[str, int] = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if pattern in msg_lower:
                score += 1
        if score > 0:
            scores[intent] = score

    # Sort by score descending
    sorted_intents = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)

    # Keep top 3 intents max
    matched = sorted_intents[:3]

    # Always include conversation as fallback
    if not matched:
        matched.append("conversation")

    return matched


def select_tools(intents: List[str]) -> List[str]:
    """Select tool names based on classified intents.

    Always includes ALWAYS_INCLUDE tools UNLESS the ONLY intent is 'conversation'.
    Returns deduplicated list of tool names.
    """
    tool_names: Set[str] = set()

    for intent in intents:
        tools = INTENT_TO_TOOLS.get(intent, set())
        tool_names.update(tools)

    # Only add always-include tools if there's a non-conversation intent
    non_conversation = [i for i in intents if i != "conversation"]
    if non_conversation:
        tool_names.update(ALWAYS_INCLUDE)

    return list(tool_names)


def select_tools_for_message(user_message: str) -> List[str]:
    """One-shot: classify intent and select tools for a message."""
    intents = classify_intent(user_message)
    return select_tools(intents)
