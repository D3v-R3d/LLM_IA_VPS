"""
Qdrant Collection Initialization

Creates default collections at startup.
"""

import logging
from app.services.document.vector_storage import VectorStorageService
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_qdrant_collections():
    """Initialize default Qdrant collections."""
    vector_service = VectorStorageService(url=settings.QDRANT_URL)
    
    default_collections = [
        {"name": "web_content", "vector_size": 768, "distance": "COSINE"},
        {"name": "document", "vector_size": 768, "distance": "COSINE"},
        {"name": "message", "vector_size": 768, "distance": "COSINE"},
    ]
    
    for coll in default_collections:
        try:
            if not vector_service.collection_exists(coll["name"]):
                vector_service.create_collection(
                    collection_name=coll["name"],
                    vector_size=coll["vector_size"],
                    distance=coll["distance"]
                )
                logger.info(f"Created Qdrant collection: {coll['name']}")
            else:
                logger.info(f"Collection already exists: {coll['name']}")
        except Exception as e:
            logger.error(f"Failed to create collection {coll['name']}: {e}")
    
    vector_service.close()


if __name__ == "__main__":
    init_qdrant_collections()