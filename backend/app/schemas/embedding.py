from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID


class EmbedDocumentRequest(BaseModel):
    document_id: UUID


class EmbedDocumentsRequest(BaseModel):
    document_ids: List[UUID]


class EmbedResult(BaseModel):
    chunks_processed: int
    success: bool
    document_id: Optional[UUID] = None


class EmbedMultipleResult(BaseModel):
    total_chunks: int
    successful_docs: int
    total_documents: int


class SearchSimilarRequest(BaseModel):
    query_text: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=100)
    score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    id: str
    score: float
    payload: Dict[str, Any]


class SearchSimilarResponse(BaseModel):
    results: List[SearchResultItem]
    query_text: str