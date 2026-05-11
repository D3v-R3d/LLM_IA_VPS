"""
qdrant_sync.py

ONLY JSON tool definitions → Qdrant ingestion.
No search logic here (see registry.py).
"""

import hashlib
import json
import glob
import logging
import os
from typing import Dict, List

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "tools_index"
VECTOR_SIZE = 768


def _load_tool_definitions() -> Dict:
    """Load all tool definitions from JSON files."""
    tools = {}
    pattern = os.path.join(os.path.dirname(__file__), "../agent_tools/*_tools.json")
    for filepath in glob.glob(pattern):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                tools.update(data)
                logger.info(f"Loaded {len(data)} tools from {filepath.split('/')[-1]}")
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
    return tools


async def sync_tools_to_qdrant():
    """Load tools and sync to Qdrant with real embeddings."""
    logger.info("Starting tool registry sync...")

    from app.services.document.vector_storage import VectorStorageService
    from app.services.tool_registry.registry import get_embeddings

    svc = VectorStorageService.get_instance(url=settings.QDRANT_URL)
    if not svc.collection_exists(COLLECTION_NAME):
        svc.create_collection(collection_name=COLLECTION_NAME, vector_size=VECTOR_SIZE, distance="COSINE")
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        logger.info(f"Collection {COLLECTION_NAME} already exists")

    tools = _load_tool_definitions()
    if not tools:
        logger.warning("No tools loaded")
        return 0

    embeddings_svc = get_embeddings()

    vectors, payloads, ids = [], [], []
    for tool_name, definition in tools.items():
        try:
            definition["name"] = tool_name
            text = _build_embedding_text(tool_name, definition)
            vector = embeddings_svc.embed(text)
            point_id = int(hashlib.md5(tool_name.encode()).hexdigest()[:8], 16)
            vectors.append(vector)
            ids.append(point_id)
            payloads.append({
                "name": tool_name,
                "description": definition.get("description", ""),
                "semantic_anchor": definition.get("semantic_anchor", ""),
                "intent_type": definition.get("intent_type", ""),
                "tool_family": definition.get("tool_family", ""),
                "category": definition.get("category", ""),
                "keywords": definition.get("keywords", [])[:5],
                "aliases": definition.get("aliases", [])[:3],
                "negative_keywords": definition.get("negative_keywords", []),
                "examples": definition.get("examples", [])[:2],
                "use_cases": definition.get("use_cases", []),
                "tool_class": definition.get("tool_class", ""),
                "embedding_boost": definition.get("embedding_boost", 1.0),
                "priority": definition.get("priority", 1),
            })
        except Exception as e:
            logger.debug(f"Prep skip: {tool_name}: {e}")

    if not ids:
        return 0

    success = svc.upsert_points(collection_name=COLLECTION_NAME, vectors=vectors, payloads=payloads, ids=ids)

    if success:
        logger.info(f"Tool registry: {len(ids)} tools upserted")
    else:
        logger.warning("Qdrant upsert failed")

    return len(ids)


def init_tool_registry() -> int:
    """Initialize tool registry at startup. Returns number of indexed tools."""
    result = sync_tools_to_qdrant_sync()
    if result and isinstance(result, int):
        from app.services.tool_registry import set_indexed_count
        set_indexed_count(result)
        return result
    return 0


def sync_tools_to_qdrant_sync():
    """Sync tools synchronously (for startup)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(sync_tools_to_qdrant())

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, sync_tools_to_qdrant()).result(timeout=120)


def _build_embedding_text(tool_name: str, definition: Dict) -> str:
    """Build text for embedding using all semantic fields."""
    parts = [
        tool_name,
        definition.get("semantic_anchor", ""),
        definition.get("description", ""),
        definition.get("intent_type", ""),
        definition.get("tool_family", ""),
        " ".join(definition.get("keywords", [])),
        " ".join(definition.get("aliases", [])),
        " ".join(definition.get("examples", [])),
        " ".join(definition.get("use_cases", [])),
    ]
    return " | ".join(p for p in parts if p)
