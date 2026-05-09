"""
Intent Classifier

Keyword-based intent classification with word boundary matching.
No LLM calls needed — fast, deterministic, lightweight.
"""

import re
from typing import List, Dict, Set

INTENT_PATTERNS: Dict[str, List[str]] = {
    "file_operation": [
        r"\bread\b", r"\bwrite\b", r"\bedit\b", r"\bglob\b", r"\bgrep\b", r"\bls\b", r"\bcat\b",
        r"\bchmod\b", r"\bchown\b", r"\bmkdir\b", r"\brmdir\b",
        r"\blist\b", r"\bdirectory\b", r"\bfolder\b", r"\bcreate file\b", r"\bmodify\b",
        r"\bdelete file\b", r"\brename\b", r"\bmove\b", r"\bcopy\b",
        r"\bfichier\b", r"\bdossier\b", r"\blire\b", r"\becrire\b", r"\bediter\b",
        r"\bcontenu du\b", r"\bliste les\b", r"\baffiche\b", r"\bouvre\b", r"\bvois\b",
        r"\bchemin\b", r"\bchemin absolu\b", r"\bchemin relatif\b",
    ],
    "web_search": [
        r"\bsearch\b", r"\bfind\b", r"\blook up\b", r"\bgoogle\b", r"\bwhat is\b",
        r"\bwho is\b", r"\blatest\b", r"\bnews\b", r"\btell me about\b",
        r"\binformation about\b", r"\bresearch\b", r"\bwikihow\b", r"\bstackoverflow\b",
        r"\bcherche\b", r"\brecherche\b", r"\btrouve\b", r"\binternet\b",
        r"\bweb\b", r"\binformation sur\b", r"\bva voir\b",
        r"\bquel est\b", r"\bqui est\b", r"\bactualite\b",
        r"\bmeme\b", r"\bimage\b", r"\bphoto\b", r"\bpicture\b", r"\bgif\b", r"\bvideo\b",
        r"\btuto\b", r"\btutorial\b", r"\bdoc\b", r"\bdocumentation\b",
        r"\bpdf\b", r"\blivre\b", r"\blivres\b",
    ],
    "web_fetch": [
        r"\bfetch\b", r"\bscrape\b", r"\bscrappe\b", r"\bget content\b", r"\bextract\b",
        r"\bdownload page\b", r"\bopen url\b", r"\bvisit\b", r"\bpage web\b",
        r"\burl\b", r"\bsite\b", r"\bsite web\b",
        r"\b recupere\b", r"\b recuperer\b", r"\bextraire\b",
    ],
    "code_execution": [
        r"\brun\b", r"\bexecute\b", r"\bbash\b", r"\bcommand\b", r"\bterminal\b",
        r"\bscript\b", r"\bshell\b", r"\bpython\b", r"\bnode\b", r"\bnpm\b",
        r"\bcompile\b", r"\bbuild\b", r"\bruntime\b",
        r"\bexecute\b", r"\bcommande\b", r"\bconsole\b",
    ],
    "docker": [
        r"(?<!/)\bdocker ps\b", r"(?<!/)\bdocker logs\b", r"(?<!/)\bdocker run\b", r"(?<!/)\bdocker pull\b",
        r"(?<!/)\bdocker stop\b", r"(?<!/)\bdocker start\b", r"(?<!/)\bdocker restart\b",
        r"(?<!/)\bdocker exec\b", r"(?<!/)\bdocker images\b", r"(?<!/)\bdocker container",
        r"(?<!/)\bdocker compose\b", r"(?<!/)\bdocker-compose",
        r"\bdockerfile\b", r"\bdocker-compose\.yml\b", r"\bdocker-compose\.yaml\b",
    ],
    "git": [
        r"\bgit\b", r"\bgit commit\b", r"\bgit push\b", r"\bgit pull\b", r"\bgit branch\b", r"\bgit merge\b",
        r"\bgit status\b", r"\bgit log\b", r"\bgit checkout\b", r"\bgit clone\b", r"\bgit diff\b",
        r"\bgithub\b", r"\bgitlab\b", r"\bbitbucket\b",
        r"\brepo\b", r"\brepository\b", r"\bcommit\b", r"\bmerge request\b", r"\bpull request\b",
    ],
    "database": [
        r"\bpostgres\b", r"\bpostgres query\b", r"\bpostgres list\b", r"\bpostgres describe\b",
        r"\bpostgresql\b", r"\bsql\b", r"\bsql query\b", r"\bexecuter sql\b", r"\brequete sql\b",
        r"\bbase de donnees\b", r"\bbase de données\b", r"\bbdd\b",
        r"\blist tables\b", r"\bdescribe table\b", r"\bselect\b", r"\binsert\b", r"\bupdate\b", r"\bdelete\b",
        r"\brequête\b", r"\btable\b", r"\bcolonnes\b", r"\blignes\b",
    ],
    "nas": [
        r"\bnas\b", r"\bsynology\b", r"\bfile station\b", r"\bquickconnect\b",
        r"\bshare\b", r"\bshared folder\b", r"\bdrive\b", r"\bnetwork drive\b", r"\bstorage\b",
        r"\bpartage\b", r"\bdossier partage\b", r"\bsamba\b",
    ],
    "telegram": [
        r"\bsend message\b", r"\bsend\b.*message", r"\bnotify\b", r"\bnotification\b",
        r"\bbroadcast\b", r"\btelegram\b", r"\bsend notification\b",
        r"\benvoie\b", r"\benvoi\b", r"\bmessage\b",
    ],
    "note_taking": [
        r"\bremember\b", r"\bremembre\b", r"\bnote\b", r"\bsave\b", r"\bwrite note\b",
        r"\btake note\b", r"\bstore this\b", r"\bécris\b", r"\bécrire\b",
        r"\bsouviens\b", r"\bretenir\b", r"\bsauvegarde\b", r"\bsauve\b",
        r"\bcrée\b", r"\bcréer\b", r"\bmémorise\b",
    ],
    "search_stored": [
        r"\bsearch stored\b", r"\bfind in my\b", r"\bremember about\b",
        r"\bwhat did i save\b", r"\bsearch content\b", r"\bsearch my\b",
        r"\bcherche dans\b", r"\brecherche dans\b", r"\btrouve dans\b",
        r"\bparmi mes\b", r"\bdans mes notes\b", r"\bdans mes fichiers\b",
        r"\bcherche mes\b", r"\brecherche mes\b",
    ],
    "conversation": [
        r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bbonjour\b", r"\bsalut\b", r"\bbonsoir\b",
        r"\bhelp\b", r"\baide\b", r"\bwho are you\b", r"\bwhat can you\b", r"\bque peux tu\b",
        r"\bhow are you\b", r"\bça va\b", r"\bca va\b", r"\bvas tu\b",
        r"\bthanks\b", r"\bmerci\b", r"\bthank you\b",
        r"\bqui es tu\b", r"\bqui est tu\b", r"\bwhat are you\b",
        r"\bau revoir\b", r"\bbye\b", r"\bgoodbye\b",
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
    """Classify user intent based on keyword matching with word boundaries.

    Returns list of matched intent names, ordered by match confidence.
    Always includes 'conversation' as fallback.
    """
    msg_lower = user_message.lower()
    matched: List[str] = []
    scores: Dict[str, int] = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            try:
                if re.search(pattern, msg_lower):
                    score += 1
            except re.error:
                # Fallback to simple match if regex is invalid
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
