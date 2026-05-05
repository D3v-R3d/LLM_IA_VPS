"""
Chunking Service

Splits text into overlapping chunks for embedding.
"""

from typing import List, Optional, Dict, Any


class ChunkingService:
    """
    Service for splitting text into chunks for embedding.

    Chunks are overlapping to preserve context at boundaries.
    Each chunk includes metadata for traceability.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunking service.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size before early break
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to split
            document_id: Optional document identifier for tracking

        Returns:
            List of chunk dictionaries with keys:
            - text: chunk content
            - chunk_index: position in document
            - start_char: character offset start
            - end_char: character offset end
            - document_id: source document
        """
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if len(chunk_text) < self.min_chunk_size and start > 0:
                break

            chunk = {
                "text": chunk_text,
                "chunk_index": len(chunks),
                "start_char": start,
                "end_char": end,
                "document_id": document_id
            }
            chunks.append(chunk)

            if end >= text_length:
                break

            start = end - self.chunk_overlap

        return chunks

    def chunk_texts(
        self,
        texts: List[str],
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk multiple texts into a single list.

        Args:
            texts: List of texts to chunk
            document_id: Optional document identifier

        Returns:
            Combined list of chunks
        """
        all_chunks = []
        for text in texts:
            chunks = self.chunk_text(text, document_id)
            all_chunks.extend(chunks)
        return all_chunks

    def chunk_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.

        Args:
            documents: List of document dicts with id, name, content_raw

        Returns:
            Combined list of chunks with document metadata
        """
        all_chunks = []
        for doc in documents:
            doc_id = doc.get("id")
            content = doc.get("content_raw", "")
            chunks = self.chunk_text(content, doc_id)
            for chunk in chunks:
                chunk["document_name"] = doc.get("name", "")
            all_chunks.extend(chunks)
        return all_chunks