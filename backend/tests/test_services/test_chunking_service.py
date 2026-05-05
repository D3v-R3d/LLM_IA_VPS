import pytest
from app.services.document.chunking import ChunkingService


class TestChunkingService:
    def test_chunk_text_basic(self):
        service = ChunkingService(chunk_size=50, chunk_overlap=10, min_chunk_size=10)
        text = "This is a longer piece of text that should be split into multiple chunks based on the chunk size configuration."

        chunks = service.chunk_text(text)

        assert len(chunks) > 1
        assert all("text" in chunk for chunk in chunks)
        assert all("chunk_index" in chunk for chunk in chunks)
        assert all("start_char" in chunk for chunk in chunks)
        assert all("end_char" in chunk for chunk in chunks)

    def test_chunk_text_short_text(self):
        service = ChunkingService(chunk_size=500, chunk_overlap=50, min_chunk_size=100)
        text = "Short text"

        chunks = service.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_chunk_text_empty(self):
        service = ChunkingService()

        chunks = service.chunk_text("")
        assert len(chunks) == 0

        chunks = service.chunk_text(None)
        assert len(chunks) == 0

    def test_chunk_text_preserves_order(self):
        service = ChunkingService(chunk_size=20, chunk_overlap=5)
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        chunks = service.chunk_text(text)

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_chunk_documents(self):
        service = ChunkingService(chunk_size=20, chunk_overlap=5, min_chunk_size=5)
        documents = [
            {"id": "doc1", "name": "Document 1", "content_raw": "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 3},
            {"id": "doc2", "name": "Document 2", "content_raw": "1234567890" * 5}
        ]

        chunks = service.chunk_documents(documents)

        assert len(chunks) > 2
        assert any(c["document_id"] == "doc1" for c in chunks)
        assert any(c["document_id"] == "doc2" for c in chunks)

    def test_chunk_indices_sequential(self):
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        text = "0123456789" * 5

        chunks = service.chunk_text(text)

        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))