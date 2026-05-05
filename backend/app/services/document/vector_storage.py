"""
Vector Storage Service

Stores and retrieves vector embeddings in Qdrant.
Provides all Qdrant operations for document embeddings.
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from uuid import uuid4


class VectorStorageService:
    """
    Service for storing and searching vectors in Qdrant.

    Handles collection management, point operations, and search.
    """

    def __init__(self, url: str = "http://qdrant:6333", port: int = 6333):
        """
        Initialize vector storage service.

        Args:
            url: Qdrant server hostname
            port: Qdrant REST API port
        """
        self.url = url
        self.port = port
        self.client = QdrantClient(url=url, port=port)

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 768,
        distance: str = "COSINE"
    ) -> bool:
        """
        Create a new collection for storing vectors.

        Args:
            collection_name: Unique name for collection
            vector_size: Dimensionality of vectors
            distance: Distance metric (COSINE, EUCLID, DOT)

        Returns:
            True if created successfully
        """
        try:
            distance_map = {
                "COSINE": Distance.COSINE,
                "EUCLID": Distance.EUCLID,
                "DOT": Distance.DOT
            }
            dist = distance_map.get(distance.upper(), Distance.COSINE)

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=dist)
            )
            return True
        except Exception:
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if collection exists.

        Args:
            collection_name: Name of collection

        Returns:
            True if collection exists
        """
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False

    def ensure_collection(
        self,
        collection_name: str,
        vector_size: int = 768
    ) -> bool:
        """
        Ensure collection exists, create if not.

        Args:
            collection_name: Collection name
            vector_size: Vector dimensions

        Returns:
            True if collection exists or was created
        """
        if not self.collection_exists(collection_name):
            return self.create_collection(collection_name, vector_size)
        return True

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Insert vectors into collection.

        Args:
            collection_name: Target collection
            vectors: List of vectors to insert
            payloads: Optional metadata per vector

        Returns:
            True if successful
        """
        try:
            points = []
            for i, vector in enumerate(vectors):
                point_id = str(uuid4())
                payload = payloads[i] if payloads and i < len(payloads) else {}

                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                ))

            self.client.upsert(collection_name=collection_name, points=points)
            return True
        except Exception:
            return False

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            collection_name: Collection to search
            query_vector: Query vector
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of results with id, score, payload
        """
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload
                }
                for r in results
            ]
        except Exception:
            return []

    def scroll_points(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[str] = None,
        with_vectors: bool = False
    ) -> Dict[str, Any]:
        """
        Scroll through points in collection with pagination.

        Args:
            collection_name: Collection name
            limit: Maximum points to return
            offset: Point ID to start from
            with_vectors: Include vectors in response

        Returns:
            Dict with points and next_page_offset
        """
        try:
            results = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_vectors=with_vectors
            )

            return {
                "points": [
                    {
                        "id": p.id,
                        "vector": p.vector,
                        "payload": p.payload,
                        "score": getattr(p, 'score', None)
                    }
                    for p in results.points
                ],
                "next_page_offset": results.next_page_offset
            }
        except Exception:
            return {"points": [], "next_page_offset": None}

    def count_points(
        self,
        collection_name: str,
        count_filter: Optional[Dict[str, Any]] = None,
        exact: bool = True
    ) -> int:
        """
        Count points in collection.

        Args:
            collection_name: Collection name
            count_filter: Optional filter conditions
            exact: Return exact count

        Returns:
            Number of points
        """
        try:
            result = self.client.count(
                collection_name=collection_name,
                count_filter=count_filter,
                exact=exact
            )
            return result.count
        except Exception:
            return 0

    def get_point(
        self,
        collection_name: str,
        point_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single point by ID.

        Args:
            collection_name: Collection name
            point_id: Point ID

        Returns:
            Point data or None
        """
        try:
            results = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
                with_vectors=False
            )
            if results:
                p = results[0]
                return {
                    "id": p.id,
                    "vector": p.vector,
                    "payload": p.payload
                }
            return None
        except Exception:
            return None

    def search_batch(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Search with multiple query vectors.

        Args:
            collection_name: Collection to search
            query_vectors: List of query vectors
            limit: Max results per query
            score_threshold: Minimum score

        Returns:
            List of result lists
        """
        try:
            results = self.client.search_batch(
                collection_name=collection_name,
                query_vector=query_vectors,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                [
                    {"id": r.id, "score": r.score, "payload": r.payload}
                    for r in result_set
                ]
                for result_set in results
            ]
        except Exception:
            return []

    def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_type: str = "text"
    ) -> bool:
        """
        Create index on payload field for faster filtering.

        Args:
            collection_name: Collection name
            field_name: Field to index
            field_type: Field type (text, integer, float, bool)

        Returns:
            True if successful
        """
        try:
            from qdrant_client.models import FieldIndex, PayloadSchemaType

            schema_type_map = {
                "text": PayloadSchemaType.TEXT,
                "integer": PayloadSchemaType.INTEGER,
                "float": PayloadSchemaType.FLOAT,
                "bool": PayloadSchemaType.BOOL
            }

            schema_type = schema_type_map.get(field_type, PayloadSchemaType.TEXT)

            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema_type
            )
            return True
        except Exception:
            return False

    def recommend(
        self,
        collection_name: str,
        positive_ids: List[str],
        negative_ids: Optional[List[str]] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar points using other points as reference.

        Args:
            collection_name: Collection name
            positive_ids: Point IDs to find similar to
            negative_ids: Point IDs to avoid
            limit: Max results
            score_threshold: Minimum score

        Returns:
            List of result dicts
        """
        try:
            from qdrant_client.models import RecommendStrategy

            results = self.client.recommend(
                collection_name=collection_name,
                positive=positive_ids,
                negative=negative_ids or [],
                limit=limit,
                score_threshold=score_threshold,
                strategy=RecommendStrategy.AVERAGE
            )

            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in results
            ]
        except Exception:
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete entire collection.

        Args:
            collection_name: Collection to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection metadata.

        Args:
            collection_name: Collection name

        Returns:
            Dict with collection info or None
        """
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception:
            return None

    def health_check(self) -> bool:
        """
        Check if Qdrant is reachable.

        Returns:
            True if healthy
        """
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False