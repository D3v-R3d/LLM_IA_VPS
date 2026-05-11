"""
Intent Classifier

Keyword-based intent classification with word boundary matching.
No LLM calls needed — fast, deterministic, lightweight.
"""

import re
from typing import List, Dict, Set, Optional

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
    # ── Granular NAS intents ─────────────────────────────────────
    "nas_list_shares": [
        r"\blist shares\b", r"\bshow shares\b", r"\bliste.*partage\b", r"\bpartages\b",
        r"\bshared folders\b", r"\blist.*dossier.*partage\b",
        r"\bpartage NAS\b", r"\bmes partages\b", r"\bvoir les partages\b",
        r"\bliste partage\b", r"\baffiche.*partage\b",
    ],
    "nas_list_folder": [
        r"\blist folder\b", r"\bopen folder\b", r"\bshow folder\b",
        r"\bcontenu dossier\b", r"\bcontenu du dossier\b",
        r"\bliste.*fichier\b", r"\bexplore\b", r"\bnavigue\b",
        r"\bvoir contenu\b", r"\baffiche dossier\b",
        r"\bparcourir\b", r"\bbrowse\b",
        r"\blist.*nas\b", r"\bfolder NAS\b",
    ],
    "nas_find_file": [
        r"\bfind file\b", r"\bsearch file\b", r"\blocate file\b",
        r"\btrouve fichier\b", r"\brecherche fichier\b",
        r"\bfichier.*nas\b", r"\bfichier sur nas\b",
        r"\bchercher fichier\b", r"\bfile.*where\b", r"\bwhere is file\b",
        r"\btrouve.*fichier\b",
    ],
    "nas_find_folder": [
        r"\bfind folder\b", r"\bsearch folder\b", r"\blocate folder\b",
        r"\btrouve dossier\b", r"\brecherche dossier\b",
        r"\bdossier.*nas\b", r"\bdossier sur nas\b",
        r"\bchercher dossier\b", r"\bwhere is folder\b",
        r"\btrouve.*dossier\b",
    ],
    "nas_search": [
        r"\bsearch nas\b", r"\bsearch synology\b",
        r"\bfind on nas\b", r"\bfind on synology\b",
        r"\bnas search\b", r"\bsynology search\b",
        r"\brecherche nas\b", r"\bchercher nas\b",
        r"\btrouve sur nas\b", r"\bchercher sur nas\b",
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
    "model_switch",
}

INTENT_TO_PRIMARY_TOOL: Dict[str, Optional[str]] = {
    "calculator": "calculator",
    "weather": "weather",
    "time": "time_tool",
    "web_fetch": "web_fetch",
    "file_operation": "read_file",
    "database": "postgres_query_read",
    "docker": "docker_exec",
    "code_execution": "bash",
    "git": "git",
    "nas_list_shares": "nas_list_share",
    "nas_list_folder": "nas_list_folder",
    "nas_find_file": "nas_find_file",
    "nas_find_folder": "nas_find_folder",
    "nas_search": "nas_search",
    "telegram": "telegram_send_message",
    "search_stored": "search_stored_content",
    "conversation": None,
    "general_chat": None,
}


def _classify_nas_intent(msg_lower: str) -> Optional[str]:
    """Specialized NAS intent classifier - returns most specific NAS intent.

    Priority: find_file > find_folder > list_folder > list_shares > search
    """
    # Most specific patterns first
    if re.search(r"\btrouve.*fichier\b", msg_lower):
        return "nas_find_file"
    if re.search(r"\bfind file\b", msg_lower):
        return "nas_find_file"
    if re.search(r"\bsearch file\b", msg_lower):
        return "nas_find_file"
    if re.search(r"\blocate file\b", msg_lower):
        return "nas_find_file"
    if re.search(r"\bfichier.*nas\b", msg_lower):
        return "nas_find_file"

    if re.search(r"\btrouve.*dossier\b", msg_lower):
        return "nas_find_folder"
    if re.search(r"\bfind folder\b", msg_lower):
        return "nas_find_folder"
    if re.search(r"\bsearch folder\b", msg_lower):
        return "nas_find_folder"
    if re.search(r"\blocate folder\b", msg_lower):
        return "nas_find_folder"

    if re.search(r"\bcontenu.*dossier\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\blist folder\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\bopen folder\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\bshow folder\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\bexplore\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\bparcourir\b", msg_lower):
        return "nas_list_folder"
    if re.search(r"\bbrowse\b", msg_lower):
        return "nas_list_folder"

    if re.search(r"\bpartages?\b", msg_lower):
        return "nas_list_shares"
    if re.search(r"\blist shares?\b", msg_lower):
        return "nas_list_shares"
    if re.search(r"\bshow shares?\b", msg_lower):
        return "nas_list_shares"

    # Generic NAS search fallback
    if re.search(r"\bnas\b", msg_lower):
        return "nas_search"
    if re.search(r"\bsynology\b", msg_lower):
        return "nas_search"
    if re.search(r"\bsearch.*synology\b", msg_lower):
        return "nas_search"

    return None


def classify_intent(user_message: str) -> List[str]:
    """Classify user intent based on keyword matching with word boundary matching.

    Returns list of matched intent names, ordered by match confidence.
    Always includes 'conversation' as fallback.
    """
    msg_lower = user_message.lower()
    matched: List[str] = []
    scores: Dict[str, int] = {}

    # ── Check for granular NAS intents first ──────────────────────
    nas_intent = _classify_nas_intent(msg_lower)
    if nas_intent:
        return [nas_intent]

    # ── General intent classification ──────────────────────────────
    for intent, patterns in INTENT_PATTERNS.items():
        # Skip old generic nas pattern (replaced by granular intents)
        if intent == "nas":
            continue
        score = 0
        for pattern in patterns:
            try:
                if re.search(pattern, msg_lower):
                    score += 1
            except re.error:
                if pattern in msg_lower:
                    score += 1
        if score > 0:
            scores[intent] = score

    sorted_intents = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    matched = sorted_intents[:3]

    if not matched:
        matched.append("conversation")

    return matched


def classify_message(user_message: str) -> Dict:
    """Full intent classification returning intent, tool, confidence, and complexity.

    Used by the orchestrator for routing decisions.
    """
    msg = user_message.strip().lower()

    # ── Hard routing fast paths ──────────────────────────
    if re.search(r"\d+\s*[\+\-\*\/]\s*\d+", msg):
        return {"intent": "calculator", "tool": "calculator", "confidence": 0.99, "complexity": 1}

    if any(x in msg for x in ["weather", "météo", "temperature", "forecast"]):
        return {"intent": "weather", "tool": "weather", "confidence": 0.97, "complexity": 1}

    if any(x in msg for x in ["time", "heure", "date", "today"]):
        return {"intent": "time", "tool": "time_tool", "confidence": 0.96, "complexity": 1}

    # ── Check granular NAS intents first ───────────────────
    nas_intent = _classify_nas_intent(msg)
    if nas_intent:
        return {
            "intent": nas_intent,
            "tool": INTENT_TO_PRIMARY_TOOL.get(nas_intent),
            "confidence": 0.9,
            "complexity": 1,
        }

    # ── Keyword-based classification ─────────────────────
    intents = classify_intent(user_message)

    primary_intent = intents[0] if intents else "conversation"
    mapped_intent = primary_intent if primary_intent != "conversation" else "general_chat"

    primary_tool = INTENT_TO_PRIMARY_TOOL.get(primary_intent)

    confidence = 0.8 if primary_intent != "conversation" else 0.55
    complexity = min(len(intents) + 1, 5)

    return {
        "intent": mapped_intent,
        "tool": primary_tool,
        "confidence": confidence,
        "complexity": complexity,
    }