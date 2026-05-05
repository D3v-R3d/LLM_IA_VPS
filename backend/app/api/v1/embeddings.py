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
from app.services.embedding_service import EmbeddingService
from app.services.document_service import DocumentService
from app.models.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

embedding_service = EmbeddingService()
document_service = DocumentService()


@router.post("/document", response_model=EmbedResult)
async def embed_document(
    request: EmbedDocumentRequest,
    db: Session = Depends(get_db)
):
    document = document_service.get_by_id(db, request.document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    doc_dict = {
        "id": str(document.id),
        "name": document.name,
        "content_raw": document.content_raw
    }

    result = await embedding_service.embed_document(doc_dict)

    if result["success"]:
        document_service.mark_as_embedded(db, request.document_id)

    return EmbedResult(
        chunks_processed=result["chunks_processed"],
        success=result["success"],
        document_id=request.document_id
    )


@router.post("/documents", response_model=EmbedMultipleResult)
async def embed_documents(
    request: EmbedDocumentsRequest,
    db: Session = Depends(get_db)
):
    documents = []
    for doc_id in request.document_ids:
        document = document_service.get_by_id(db, doc_id)
        if document:
            documents.append({
                "id": str(document.id),
                "name": document.name,
                "content_raw": document.content_raw
            })

    result = await embedding_service.embed_documents(documents)

    for doc in documents:
        document_service.mark_as_embedded(db, doc["id"])

    return EmbedMultipleResult(
        total_chunks=result["total_chunks"],
        successful_docs=result["successful_docs"],
        total_documents=result["total_documents"]
    )


@router.post("/search", response_model=SearchSimilarResponse)
async def search_similar(
    request: SearchSimilarRequest,
    db: Session = Depends(get_db)
):
    results = await embedding_service.search_similar(
        query_text=request.query_text,
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
    return embedding_service.health_check()