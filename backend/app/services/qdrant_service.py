"""
Qdrant Vector Database Service Module

This module provides integration with Qdrant, a vector similarity search engine.
Qdrant is used for storing and searching embeddings (vector representations of text).

Qdrant provides:
- Fast vector similarity search
- CRUD operations on collections of vectors
- Payload filtering
- Range queries and global nearest neighbors

Usage:
    from app.services.qdrant_service import QdrantService

    qdrant = QdrantService(url="http://qdrant:6333")
    qdrant.create_collection("my_collection", vector_size=1536)
    qdrant.insert_vectors("my_collection", [[0.1, 0.2, ...]], [{"text": "sample"}])
    results = qdrant.search("my_collection", query_vector=[0.1, 0.2, ...])
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse
import uuid


class QdrantService:
    """
    Service class for interacting with Qdrant vector database.

    Qdrant stores vectors (embeddings) and enables fast similarity search.
    Each vector can have optional payload data (metadata) attached.

    Attributes:
        url: Hostname of the Qdrant server
        port: Port number of the Qdrant REST API
        client: QdrantClient instance for making API calls
    """

    def __init__(self, url: str = None, port: int = 6333):
        """
        Initialize the Qdrant service client.

        Args:
            url: Full URL or hostname of Qdrant server.
                 If a full URL is provided (e.g., "http://qdrant:6333"),
                 the hostname and port are extracted from it.
                 If just a hostname is provided, the port argument is used.
            port: Default port number (6333) used if URL doesn't contain one.
                  Only used when url parameter is a hostname without port.
        """
        if url:
            # Parse URL to extract hostname and port
            # urlparse("http://qdrant:6333") -> hostname="qdrant", port=6333
            parsed = urlparse(url)
            # Use hostname from URL, fallback to original URL if no hostname
            self.url = parsed.hostname or url
            # Use port from URL, fallback to default port if not specified
            self.port = parsed.port or port
        else:
            # Use defaults if no URL provided
            self.url = "localhost"
            self.port = port

        # Initialize the Qdrant client with extracted URL and port
        # This client handles all communication with the Qdrant server
        self.client = QdrantClient(url=self.url, port=self.port)

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create a new collection for storing vectors.

        A collection is like a table in a traditional database.
        All vectors in a collection have the same dimensionality.

        Args:
            collection_name: Unique name for the new collection
            vector_size: Dimensionality of vectors to be stored (default 1536)
                        Should match the embedding model output size.
            distance: Distance metric for similarity search (default COSINE).
                     Options:
                     - COSINE: Cosine similarity (recommended for text embeddings)
                     - EUCLID: Euclidean distance
                     - DOT: Dot product

        Returns:
            True if collection was created successfully, False otherwise.

        Example:
            # Create a collection for text embeddings
            success = qdrant.create_collection(
                collection_name="documents",
                vector_size=768,  # Match embedding model dimensions
                distance=Distance.COSINE
            )
        """
        try:
            # Create collection with specified vector configuration
            # VectorParams defines the size (dimensions) and distance metric
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            return True
        except Exception:
            # Return False if collection creation failed
            # (e.g., collection already exists)
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection to check

        Returns:
            True if collection exists, False otherwise.

        Example:
            if qdrant.collection_exists("documents"):
                print("Collection already exists")
        """
        try:
            # Attempt to get collection info
            # Throws exception if collection doesn't exist
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Insert vectors into a collection.

        Each vector can be associated with a payload (metadata).
        Payloads are stored alongside vectors and can be used for filtering.

        Args:
            collection_name: Name of the target collection
            vectors: List of vector arrays to insert.
                    Each vector should be a list of floats.
            payloads: Optional list of metadata dicts, one per vector.
                      If provided, must have the same length as vectors.
                      Example: [{"text": "Document 1"}, {"text": "Document 2"}]

        Returns:
            True if insertion was successful, False otherwise.

        Example:
            vectors = [
                [0.1, 0.2, 0.3, ...],  # 1536-dimensional vector
                [0.4, 0.5, 0.6, ...]
            ]
            payloads = [
                {"text": "First document", "category": "science"},
                {"text": "Second document", "category": "history"}
            ]
            success = qdrant.insert_vectors("documents", vectors, payloads)
        """
        try:
            # Prepare points for insertion
            points = []

            for i, vector in enumerate(vectors):
                # Generate unique ID for each vector using UUID
                # This ensures each vector has a unique identifier
                point_id = str(uuid.uuid4())

                # Get corresponding payload if available
                # Empty dict if no payloads provided
                payload = payloads[i] if payloads else {}

                # Create PointStruct with ID, vector, and optional payload
                # PointStruct is the basic data unit in Qdrant
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

            # Upsert (insert or update) points into the collection
            # If a point with same ID exists, it's updated
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
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
        Search for similar vectors in a collection.

        Finds the k-nearest vectors to the query vector based on
        the collection's distance metric (COSINE by default).

        Args:
            collection_name: Name of the collection to search in
            query_vector: The vector to find similar vectors to
            limit: Maximum number of results to return (default 5)
            score_threshold: Optional minimum similarity score.
                            Only results with score >= threshold are returned.

        Returns:
            List of result dicts, each containing:
            - id: Unique identifier of the matched vector
            - score: Similarity score (higher = more similar)
            - payload: Metadata associated with the vector

        Example:
            results = qdrant.search(
                collection_name="documents",
                query_vector=[0.1, 0.2, 0.3, ...],
                limit=10,
                score_threshold=0.7
            )
            for result in results:
                print(f"ID: {result['id']}, Score: {result['score']}")
                print(f"Text: {result['payload']['text']}")
        """
        try:
            # Perform similarity search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )

            # Transform results into a cleaner dict format
            return [
                {
                    "id": result.id,          # Unique vector ID
                    "score": result.score,    # Similarity score
                    "payload": result.payload  # Associated metadata
                }
                for result in results
            ]
        except Exception:
            # Return empty list if search failed
            return []

    def health_check(self) -> bool:
        """
        Check if Qdrant service is healthy and reachable.

        Makes a request to list all collections as a simple health check.

        Returns:
            True if Qdrant is reachable, False otherwise.
        """
        try:
            # get_collections() returns info about all collections
            # If this succeeds, the service is healthy
            self.client.get_collections()
            return True
        except Exception:
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an entire collection and all its vectors.

        WARNING: This operation is irreversible!

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if deletion was successful, False otherwise.

        Example:
            success = qdrant.delete_collection("old_documents")
        """
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a collection.

        Args:
            collection_name: Name of the collection to inspect

        Returns:
            Dict with collection metadata:
            - name: Collection name
            - vectors_count: Number of vectors stored
            - points_count: Number of points (same as vectors_count)
            - status: Collection status (e.g., "green")

            Returns None if collection doesn't exist.

        Example:
            info = qdrant.get_collection_info("documents")
            print(f"Vectors: {info['vectors_count']}")
        """
        try:
            # Get collection information
            info = self.client.get_collection(collection_name)

            # Return structured info dict
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception:
            return None

    def scroll_points(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[str] = None,
        with_vectors: bool = False
    ) -> Dict[str, Any]:
        """
        Scroll through points in a collection with pagination.

        Useful for iterating over all points or paginating through results.

        Args:
            collection_name: Name of the collection
            limit: Maximum number of points to return (default 100)
            offset: Point ID to start from (for pagination)
            with_vectors: If True, includes vectors in response

        Returns:
            Dict containing:
            - points: List of points
            - next_page_offset: ID of next page, or None if done

        Example:
            result = qdrant.scroll_points("documents", limit=10)
            for point in result["points"]:
                print(f"ID: {point.id}")
            if result["next_page_offset"]:
                next_page = qdrant.scroll_points(
                    "documents",
                    limit=10,
                    offset=result["next_page_offset"]
                )
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
        Count points in a collection.

        Args:
            collection_name: Name of the collection
            count_filter: Optional filter conditions
            exact: If True, returns exact count (slower for large collections)

        Returns:
            Number of points in the collection.

        Example:
            count = qdrant.count_points("documents")
            filtered_count = qdrant.count_points(
                "documents",
                count_filter={"payload": {"document_id": "uuid"}}
            )
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
            collection_name: Name of the collection
            point_id: Unique ID of the point to retrieve

        Returns:
            Dict with point data (id, vector, payload, score) or None if not found.

        Example:
            point = qdrant.get_point("documents", "point-uuid")
            if point:
                print(f"Text: {point['payload']['text']}")
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
        score_threshold: Optional[float] = None,
        query_filter: Optional[Dict[str, Any]] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Search with multiple query vectors at once.

        More efficient than multiple separate searches when you need
        to search with multiple query vectors.

        Args:
            collection_name: Name of the collection to search in
            query_vectors: List of query vectors to search with
            limit: Maximum number of results per query (default 5)
            score_threshold: Optional minimum similarity score
            query_filter: Optional filter conditions

        Returns:
            List of result lists, one per query vector.

        Example:
            results = qdrant.search_batch(
                "documents",
                query_vectors=[[0.1, 0.2], [0.3, 0.4]],
                limit=5
            )
            for i, result_set in enumerate(results):
                print(f"Query {i}: {len(result_set)} results")
        """
        try:
            results = self.client.search_batch(
                collection_name=collection_name,
                query_vector=query_vectors,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )

            return [
                [
                    {
                        "id": r.id,
                        "score": r.score,
                        "payload": r.payload
                    }
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
        Create an index on a payload field for faster filtering.

        Indexes significantly speed up filtered searches on specific fields.

        Args:
            collection_name: Name of the collection
            field_name: Name of the payload field to index
            field_type: Type of the field ("text", "integer", "float", "bool", "geo", "datetime")

        Returns:
            True if index was created successfully, False otherwise.

        Example:
            qdrant.create_payload_index("documents", "document_id")
            qdrant.create_payload_index("documents", "chunk_index", "integer")
        """
        try:
            from qdrant_client.models import FieldIndex, PayloadSchemaType

            schema_type_map = {
                "text": PayloadSchemaType.TEXT,
                "integer": PayloadSchemaType.INTEGER,
                "float": PayloadSchemaType.FLOAT,
                "bool": PayloadSchemaType.BOOL,
                "geo": PayloadSchemaType.GEO,
                "datetime": PayloadSchemaType.DATETIME
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
        score_threshold: Optional[float] = None,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find similar points using other points as reference (not a query vector).

        Uses the vectors of specified points to find other similar points.
        Useful for "more like this" style recommendations.

        Args:
            collection_name: Name of the collection
            positive_ids: List of point IDs with good characteristics
            negative_ids: Optional list of point IDs to avoid
            limit: Maximum number of results (default 5)
            score_threshold: Optional minimum similarity score
            with_vectors: If True, includes vectors in results

        Returns:
            List of result dicts, each containing id, score, and payload.

        Example:
            results = qdrant.recommend(
                "documents",
                positive_ids=["known-good-point-id"],
                negative_ids=["known-bad-point-id"],
                limit=5
            )
            for r in results:
                print(f"Similar to: {r['payload']['text'][:50]}")
        """
        try:
            from qdrant_client.models import RecommendStrategy

            results = self.client.recommend(
                collection_name=collection_name,
                positive=positive_ids,
                negative=negative_ids or [],
                limit=limit,
                score_threshold=score_threshold,
                with_vectors=with_vectors,
                strategy=RecommendStrategy.AVERAGE
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