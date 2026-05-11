"""
text_processing.py

FR + EN NLP helpers:
- normalize_text()
- tokenize()
- remove_stopwords()
- stem_tokens() (simplemma FR/EN)
- expand_synonyms() (manual FR<->EN bidirectional)
- preprocess() (full pipeline, mode light without stemming)

Order: normalize → tokenize → stopwords → synonyms → stem
"""

import re
from functools import lru_cache
from typing import List, Set

import simplemma

STOPWORDS_FR = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux",
    "et", "ou", "mais", "donc", "car", "ni", "or",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "leur", "moi", "toi", "soi",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "votre", "nos", "vos", "leur",
    "qui", "que", "quoi", "dont", "où",
    "ce", "cet", "cette", "ces",
    "celui", "celle", "ceux", "celles",
    "ça", "cela", "ici", "là", "ainsi", "alors", "plus", "moins",
    "très", "bien", "mal", "tout", "tous", "toute", "toutes",
    "quel", "quelle", "quels", "quelles",
    "on", "ne", "pas", "jamais", "toujours",
    "si", "y", "en", "a", "est", "sont", "été", "être", "avoir",
    "avec", "sans", "pour", "par", "sur", "sous", "chez", "dans",
    "avant", "après", "entre", "pendant", "depuis",
    "comme", "quand", "même", "autre", "autres",
}

STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "can", "to", "of", "in", "for", "on", "by", "with",
    "at", "from", "as", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "over",
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some", "any",
    "no", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "also", "now", "here", "there", "then", "once", "ever",
}

STOPWORDS = STOPWORDS_FR | STOPWORDS_EN

SYNO_FR_EN = {
    "trouver": "find",
    "fichier": "file",
    "fichiers": "files",
    "calculer": "calculate",
    "calcul": "calculate",
    "operation": "calculate",
    "mathematique": "mathematics",
    "maths": "mathematics",
    "meteo": "weather",
    "temps": "weather",
    "film": "movie",
    "chercher": "search",
    "recherche": "search",
    "liste": "list",
    "dossier": "folder",
    "commande": "command",
    "terminal": "terminal",
    "memoire": "memory",
    "souvenir": "memory",
    "base": "database",
    "donnees": "data",
    "lecture": "read",
    "lire": "read",
    "ecriture": "write",
    "ecrire": "write",
    "modifier": "edit",
    "supprimer": "delete",
    "appeler": "call",
    "appel": "call",
    "message": "message",
    "notification": "notification",
    "pluie": "rain",
    "soleil": "sun",
    "temperature": "temperature",
    "debut": "start",
    "fin": "end",
    "copier": "copy",
    "coller": "paste",
    "couper": "cut",
    "naviguer": "browse",
    "explorer": "explore",
    "voir": "view",
    "afficher": "display",
    "ouvrir": "open",
    "creer": "create",
    "nouveau": "new",
    "vide": "empty",
    "plein": "full",
    "trouve": "find",
    "montrer": "show",
}

SYNO_EN_FR = {v: k for k, v in SYNO_FR_EN.items()}


def normalize_text(text: str) -> str:
    """Lowercase + strip."""
    return text.lower().strip()


def tokenize(text: str) -> List[str]:
    """Extract alphanumeric tokens."""
    return re.findall(r'\w+', text.lower())


def remove_stopwords(tokens: List[str], stopwords: Set[str] | None = None) -> List[str]:
    """Remove stopwords from token list."""
    sw = stopwords if stopwords is not None else STOPWORDS
    return [t for t in tokens if t not in sw]


def stem_tokens(tokens: List[str], lang: str = "en") -> List[str]:
    """
    Stem tokens using simplemma (FR + EN).
    lang: 'en' or 'fr'
    """
    if lang == "fr":
        return [simplemma.lemmatize(t, lang="fr") or t for t in tokens]
    return [simplemma.lemmatize(t, lang="en") or t for t in tokens]


def expand_synonyms(tokens: List[str], direction: str = "both") -> List[str]:
    """
    Expand tokens with FR<->EN synonyms.
    Returns deduplicated list.
    direction: 'fr_to_en', 'en_to_fr', 'both', 'none'
    """
    if direction == "none":
        return tokens

    expanded = set()
    for t in tokens:
        expanded.add(t)
        if direction in ("fr_to_en", "both"):
            if t in SYNO_FR_EN:
                expanded.add(SYNO_FR_EN[t])
        if direction in ("en_to_fr", "both"):
            if t in SYNO_EN_FR:
                expanded.add(SYNO_EN_FR[t])

    return list(expanded)


def _detect_lang(text: str) -> str:
    """Auto-detect language based on French accented characters."""
    return "fr" if any(c in "àâäçéèêëîïôùûüÿœæ" for c in text) else "en"


@lru_cache(maxsize=2048)
def preprocess(
    text: str,
    use_stemming: bool = True,
    use_synonyms: bool = True,
    use_stopwords: bool = True,
    lang: str = "auto",
) -> tuple[str, ...]:
    """
    Full preprocessing pipeline.

    Order: normalize → tokenize → stopwords → synonyms → stem

    Args:
        text: input text
        use_stemming: if False, skip stemming (light mode)
        use_synonyms: if False, skip synonym expansion
        use_stopwords: if False, skip stopword removal
        lang: 'en', 'fr', 'auto'

    Returns:
        tuple of tokens (hashable for lru_cache)
    """
    text = normalize_text(text)
    tokens = tokenize(text)

    if use_stopwords:
        tokens = remove_stopwords(tokens)

    if use_synonyms:
        tokens = expand_synonyms(tokens, direction="both")

    if lang == "auto":
        lang = _detect_lang(text)

    if use_stemming:
        tokens = stem_tokens(tokens, lang=lang)

    return tuple(tokens)
