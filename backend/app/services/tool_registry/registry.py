"""
registry.py

Tool registry: load/search/sync tools.
Orchestrates search + ranking + hybrid scoring.
"""

import glob
import json
import logging
import os
from typing import Dict, List

from app.core.config import settings

from .embeddings import get_embeddings
from .reranker import (
    VECTOR_WEIGHT,
    KEYWORD_WEIGHT,
    FUZZY_WEIGHT,
    build_tool_text,
    build_tool_token_set,
    exact_match_boost,
    fuzzy_score,
    hybrid_score,
    intent_boost,
    keyword_overlap,
    negative_penalty,
)
from .text_processing import preprocess

logger = logging.getLogger(__name__)

COLLECTION_NAME = "tools_index"
VECTOR_SIZE = 768
SCORE_THRESHOLD = 0.45


def get_all_tools() -> Dict:
    """Get all tool definitions."""
    tools = {}
    pattern = os.path.join(os.path.dirname(__file__), "../agent_tools/*_tools.json")
    for filepath in glob.glob(pattern):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                tools.update(data)
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
    return tools


def get_tools_by_category(category: str) -> Dict:
    """Filter tools by category."""
    tools = get_all_tools()
    return {k: v for k, v in tools.items() if v.get("category") == category}


def build_tool_embedding(tool: dict) -> str:
    """
    Build rich embedding text for a tool.

    Format:
    TOOL: {name}
    CATEGORY: {tool_family}
    DESCRIPTION:
    {description}
    SEMANTIC ANCHOR:
    {semantic_anchor}
    KEYWORDS:
    {keywords}
    ALIASES:
    {aliases}
    EXAMPLES:
    {examples}
    USE CASES:
    {use_cases}
    """
    name = tool.get("name", "")
    tool_family = tool.get("tool_family", tool.get("category", ""))
    description = tool.get("description", "")
    semantic_anchor = tool.get("semantic_anchor", "")
    keywords = " | ".join(tool.get("keywords", []))
    aliases = " | ".join(tool.get("aliases", []))
    examples = " | ".join(tool.get("examples", []))
    use_cases = " | ".join(tool.get("use_cases", []))

    parts = [
        f"TOOL: {name}",
        f"CATEGORY: {tool_family}",
        f"DESCRIPTION: {description}",
        f"SEMANTIC ANCHOR: {semantic_anchor}",
        f"KEYWORDS: {keywords}",
        f"ALIASES: {aliases}",
        f"EXAMPLES: {examples}",
        f"USE CASES: {use_cases}",
    ]

    return "\n".join(p for p in parts if p.split(": ", 1)[1].strip())


def build_query_embedding(query: str) -> str:
    """
    Build embedding text for a user query.

    Format:
    USER REQUEST:
    {query}
    TASK:
    find the best matching tools for this request
    """
    return f"USER REQUEST:\n{query}\nTASK:\nfind the best matching tools for this request"


def search_tools(query: str, limit: int = 5, use_stemming: bool = True) -> List[Dict]:
    """
    Search tools using Qdrant vector search + hybrid reranking.

    1. Embed query with build_query_embedding()
    2. Vector search in Qdrant (retrieve top limit*3 for recall)
    3. Hybrid reranking: vector + keyword + fuzzy with negative penalty
    4. Filter by score threshold (0.35)
    5. Return top k

    Args:
        query: user search query
        limit: max results to return
        use_stemming: if False, use light mode without stemming
    """
    embeddings_svc = get_embeddings()

    query_text = build_query_embedding(query)
    query_vector = embeddings_svc.embed(query_text)

    from app.services.document.vector_storage import VectorStorageService

    svc = VectorStorageService.get_instance(url=settings.QDRANT_URL)
    results = svc.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=limit * 3,
    )

    query_tokens = list(preprocess(query, use_stemming=use_stemming))

    scored = []
    for r in results:
        payload = r.get("payload", {})
        vector_score = r.get("score", 0.0)

        tool_token_set = build_tool_token_set(
            keywords=payload.get("keywords", []),
            aliases=payload.get("aliases", []),
            semantic_anchor=payload.get("semantic_anchor", ""),
            description=payload.get("description", ""),
            preprocess_fn=lambda f: list(preprocess(f, use_stemming=use_stemming)),
        )

        tool_text = build_tool_text(
            keywords=payload.get("keywords", []),
            aliases=payload.get("aliases", []),
            semantic_anchor=payload.get("semantic_anchor", ""),
            description=payload.get("description", ""),
        )

        neg_tokens = list(preprocess(
            " ".join(payload.get("negative_keywords", [])),
            use_stemming=False,
            use_synonyms=False,
            use_stopwords=False,
        ))

        kw_score = keyword_overlap(query_tokens, tool_token_set)
        fuz_score = fuzzy_score(query_tokens, tool_text)
        neg_mult = negative_penalty(query_tokens, neg_tokens)
        boost = exact_match_boost(query_tokens, tool_token_set)
        boost += intent_boost(query_tokens, payload.get("tool_family", ""))

        final_score = hybrid_score(
            vector_score,
            kw_score,
            fuz_score,
            neg_mult,
            boost=boost,
            vector_weight=VECTOR_WEIGHT,
            keyword_weight=KEYWORD_WEIGHT,
            fuzzy_weight=FUZZY_WEIGHT,
        )

        scored.append({
            "name": payload.get("name", ""),
            "description": payload.get("description", ""),
            "semantic_anchor": payload.get("semantic_anchor", ""),
            "intent_type": payload.get("intent_type", ""),
            "tool_family": payload.get("tool_family", ""),
            "category": payload.get("category", ""),
            "keywords": payload.get("keywords", [])[:5],
            "score": final_score,
            "vector_score": vector_score,
            "keyword_score": kw_score,
            "fuzzy_score": fuz_score,
            "negative_penalty": neg_mult,
            "boost": boost,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    names = [s["name"] for s in scored]
    vec_scores = [f"{s['vector_score']:.3f}" for s in scored]
    kw_scores = [f"{s['keyword_score']:.3f}" for s in scored]
    fuz_scores = [f"{s['fuzzy_score']:.3f}" for s in scored]
    final_scores = [f"{s['score']:.3f}" for s in scored]

    logger.info(
        "tool_search query=%s candidates=%s vector_scores=%s keyword_scores=%s fuzzy_scores=%s final_scores=%s",
        query, names[:8], vec_scores[:8], kw_scores[:8], fuz_scores[:8], final_scores[:8],
    )

    filtered = [s for s in scored if s["score"] >= SCORE_THRESHOLD]

    return filtered[:limit]
