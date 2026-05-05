"""
Embeddings API Endpoints

Endpoints for document embedding and semantic search.
Uses services from app.services.document and app.services.llm.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from app.schemas.embedding import (
    EmbedDocumentRequest,
    EmbedDocumentsRequest,
    EmbedResult,
    EmbedMultipleResult,
    SearchSimilarRequest,
    SearchSimilarResponse,
    SearchResultItem,
)
from app.services.document import ChunkingService, VectorStorageService
from app.services.llm import EmbeddingService
from app.services.document_service import DocumentService
from app.models.database import get_db
from app.core.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
VECTOR_SIZE = 768
COLLECTION_NAME = "document_chunks"


def get_embedding_service():
    """Create embedding service instance."""
    return EmbeddingService()


def get_chunking_service():
    """Create chunking service instance."""
    return ChunkingService(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def get_vector_storage():
    """Create vector storage instance."""
    return VectorStorageService()


@router.post("/document", response_model=EmbedResult)
async def embed_document(
    request: EmbedDocumentRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Embed a single document."""
    document_service = DocumentService()
    document = document_service.get_by_id(db, request.document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if str(document.user_id) != str(current_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    content = document.content_raw or ""
    if not content:
        return EmbedResult(
            chunks_processed=0,
            success=False,
            document_id=request.document_id
        )

    chunking_service = get_chunking_service()
    chunks = chunking_service.chunk_text(content, str(document.id))

    if not chunks:
        return EmbedResult(
            chunks_processed=0,
            success=False,
            document_id=request.document_id
        )

    vector_storage = get_vector_storage()
    vector_storage.ensure_collection(COLLECTION_NAME, VECTOR_SIZE)

    embedding_service = get_embedding_service()
    texts_to_embed = [chunk["text"] for chunk in chunks]
    embedding_result = await embedding_service.embed(texts_to_embed)
    embeddings = embedding_result.get("embeddings", [])

    payloads = [
        {
            "text": chunk["text"],
            "chunk_index": chunk["chunk_index"],
            "document_id": chunk["document_id"],
            "start_char": chunk["start_char"],
            "end_char": chunk["end_char"]
        }
        for chunk in chunks
    ]

    success = vector_storage.insert_vectors(
        collection_name=COLLECTION_NAME,
        vectors=embeddings,
        payloads=payloads
    )

    if success:
        document_service.mark_as_embedded(db, request.document_id)

    return EmbedResult(
        chunks_processed=len(chunks),
        success=success,
        document_id=request.document_id
    )


@router.post("/documents", response_model=EmbedMultipleResult)
async def embed_documents(
    request: EmbedDocumentsRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Embed multiple documents."""
    document_service = DocumentService()
    embedding_service = get_embedding_service()
    chunking_service = get_chunking_service()
    vector_storage = get_vector_storage()

    vector_storage.ensure_collection(COLLECTION_NAME, VECTOR_SIZE)

    documents = []
    for doc_id in request.document_ids:
        document = document_service.get_by_id(db, doc_id)
        if document and str(document.user_id) == str(current_user_id):
            documents.append({
                "id": str(document.id),
                "name": document.name,
                "content_raw": document.content_raw or ""
            })

    total_chunks = 0
    successful_docs = 0

    for doc in documents:
        chunks = chunking_service.chunk_text(doc["content_raw"], doc["id"])

        if not chunks:
            continue

        texts_to_embed = [chunk["text"] for chunk in chunks]
        embedding_result = await embedding_service.embed(texts_to_embed)
        embeddings = embedding_result.get("embeddings", [])

        payloads = [
            {
                "text": chunk["text"],
                "chunk_index": chunk["chunk_index"],
                "document_id": chunk["document_id"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"]
            }
            for chunk in chunks
        ]

        success = vector_storage.insert_vectors(
            collection_name=COLLECTION_NAME,
            vectors=embeddings,
            payloads=payloads
        )

        if success:
            total_chunks += len(chunks)
            successful_docs += 1
            document_service.mark_as_embedded(db, doc["id"])

    return EmbedMultipleResult(
        total_chunks=total_chunks,
        successful_docs=successful_docs,
        total_documents=len(documents)
    )


@router.post("/search", response_model=SearchSimilarResponse)
async def search_similar(
    request: SearchSimilarRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for similar content."""
    embedding_service = get_embedding_service()
    vector_storage = get_vector_storage()

    embedding_result = await embedding_service.embed(request.query_text)
    query_embedding = embedding_result.get("embeddings", [[]])[0]

    results = vector_storage.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=request.limit,
        score_threshold=request.score_threshold
    )

    search_results = [
        SearchResultItem(
            id=r["id"],
            score=r["score"],
            payload=r["payload"]
        )
        for r in results
    ]

    return SearchSimilarResponse(
        results=search_results,
        query_text=request.query_text
    )


@router.get("/health")
async def health_check():
    """Check embedding service health."""
    vector_storage = get_vector_storage()
    return {
        "qdrant": vector_storage.health_check(),
        "llm": True
    }