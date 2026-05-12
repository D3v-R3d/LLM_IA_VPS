"""
reranker.py

Hybrid reranking for tool search:
- keyword_overlap()
- fuzzy_score()
- negative_penalty()
- hybrid_score()

Weights are configurable constants.
"""

from typing import List, Set

from rapidfuzz import fuzz

VECTOR_WEIGHT = 0.70
KEYWORD_WEIGHT = 0.15
FUZZY_WEIGHT = 0.15


def keyword_overlap(query_tokens: List[str], tool_tokens: Set[str]) -> float:
    """
    Compute normalized keyword overlap.
    query_tokens: list of tokens (preprocessed)
    tool_tokens: set of tokens from tool fields
    Returns score between 0 and 1.
    """
    if not query_tokens or not tool_tokens:
        return 0.0

    overlap = set(query_tokens) & tool_tokens
    if not overlap:
        return 0.0

    return len(overlap) / max(len(query_tokens), 1)


def fuzzy_score(query_tokens: List[str], tool_text: str) -> float:
    """
    Fuzzy matching on raw tool text against query tokens.
    Uses fuzz.ratio (exact) with early stop at 0.95.

    FIX: removed early return at 0.85 — it could return a sub-optimal score
    if a later token produced a higher match. Now the full token list is
    always scanned; only the 0.95 early-exit (perfect match) is kept.
    """
    if not query_tokens or not tool_text:
        return 0.0

    tool_lower = tool_text.lower()
    best = 0.0
    for qt in query_tokens:
        score = fuzz.ratio(qt, tool_lower) / 100.0
        if score > best:
            best = score
        if best >= 0.95:
            return 1.0

    return best


def negative_penalty(query_tokens: List[str], negative_keywords: List[str]) -> float:
    """
    Apply multiplicative penalty if query tokens overlap negative_keywords.
    Returns penalty between 0.1 and 1.0 based on overlap ratio.
    """
    if not negative_keywords:
        return 1.0

    neg_set = set(w.lower() for w in negative_keywords)
    query_set = set(query_tokens)
    overlap = query_set & neg_set

    if not overlap:
        return 1.0

    overlap_ratio = len(overlap) / max(len(query_set), 1)
    return 0.1 + (1 - overlap_ratio)


def build_tool_token_set(
    keywords: List[str],
    aliases: List[str],
    semantic_anchor: str = "",
    description: str = "",
    preprocess_fn=None,
) -> Set[str]:
    """
    Build a token set from tool fields for matching.
    Always uses preprocess_fn if provided.

    NOTE: callers should cache the result at registry init time rather
    than rebuilding on every query. This function is intentionally stateless
    so the cache can live wherever the registry is managed.
    """
    if preprocess_fn is None:
        raise ValueError("preprocess_fn is required")

    fields = [
        semantic_anchor,
        description,
        *keywords,
        *aliases,
    ]

    all_tokens = []
    for f in fields:
        if f:
            all_tokens.extend(preprocess_fn(f))
    return set(all_tokens)


def build_tool_text(
    keywords: List[str],
    aliases: List[str],
    semantic_anchor: str = "",
    description: str = "",
) -> str:
    """
    Build raw text from tool fields for fuzzy matching.
    """
    fields = [
        semantic_anchor,
        description,
        " ".join(keywords),
        " ".join(aliases),
    ]
    return " ".join(f for f in fields if f)


def exact_match_boost(query_tokens: List[str], tool_tokens: Set[str]) -> float:
    """
    Boost score if all query tokens are found in tool tokens.

    FIX: boost is now proportional to the fraction of query tokens matched,
    so a single-token exact match on a long query does not receive the same
    +0.2 as a full multi-token exact match.

    Returns a value in [0.0, 0.2].
    """
    if not query_tokens or not tool_tokens:
        return 0.0

    matched = set(query_tokens) & tool_tokens
    if not matched:
        return 0.0

    ratio = len(matched) / len(set(query_tokens))
    return round(0.2 * ratio, 4)


def intent_boost(query_tokens: List[str], tool_family: str) -> float:
    """
    Boost if tool_family matches a query token.
    Returns 0.1 or 0.0.
    """
    if not query_tokens or not tool_family:
        return 0.0

    if tool_family.lower() in query_tokens:
        return 0.1

    return 0.0


def hybrid_score(
    vector_score: float,
    keyword_score: float,
    fuzzy: float,
    negative_mult: float,
    boost: float = 0.0,
    vector_weight: float = VECTOR_WEIGHT,
    keyword_weight: float = KEYWORD_WEIGHT,
    fuzzy_weight: float = FUZZY_WEIGHT,
) -> float:
    """
    Combine vector, keyword, fuzzy scores with negative penalty and exact match boost.
    Clamped to [0.0, 1.0].

    final = clamp((vector * vw + keyword * kw + fuzzy * fw) * negative_mult + boost, 0, 1)
    """
    raw = (
        vector_score * vector_weight
        + keyword_score * keyword_weight
        + fuzzy * fuzzy_weight
    )
    return max(0.0, min(1.0, raw * negative_mult + boost))