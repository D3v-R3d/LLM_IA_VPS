from typing import List, Optional


class ChunkingService:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, document_id: Optional[str] = None) -> List[dict]:
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]

            if len(chunk) < self.min_chunk_size and start > 0:
                break

            chunk_dict = {
                "text": chunk,
                "chunk_index": len(chunks),
                "start_char": start,
                "end_char": end,
                "document_id": document_id
            }
            chunks.append(chunk_dict)

            if end >= text_length:
                break

            start = end - self.chunk_overlap

        return chunks

    def chunk_documents(self, documents: List[dict]) -> List[dict]:
        all_chunks = []
        for doc in documents:
            doc_id = doc.get("id")
            content = doc.get("content_raw", "")
            chunks = self.chunk_text(content, doc_id)
            for chunk in chunks:
                chunk["document_id"] = doc_id
                chunk["document_name"] = doc.get("name", "")
            all_chunks.extend(chunks)
        return all_chunks