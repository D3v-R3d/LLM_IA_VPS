"""
Document Model Module

This module defines the Document entity for the Tower Project application.
Documents are files uploaded by users for processing and embedding.

Database Attributes:
- id: UUID primary key
- user_id: Foreign key to User
- name: Document name/title
- content_raw: Raw content or file path
- type: Document type (pdf, txt, md, etc.)
- created_at: Creation timestamp

Qdrant Integration:
- YES - Document chunks are OBLIGATORILY embedded for RAG
- Documents are chunked and each chunk is embedded
- Text embedded: chunk_text
- Payload per chunk: document_id, chunk_id, user_id, text, page, created_at
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class Document(Base):
    """
    Document model representing an uploaded file.

    Documents are user-uploaded files that are processed, chunked,
    and embedded for retrieval-augmented generation (RAG).

    Attributes:
        id: Unique identifier (UUID4)
        user_id: Foreign key to the User who uploaded this document
        name: Original filename or user-provided title
        content_raw: Raw text content or path to file storage
        type: Document type/format (pdf, txt, md, doc, etc.)
        created_at: Timestamp when document was uploaded

    Relationships:
        user: The User who owns this document

    RAG Processing:
        Documents should be split into chunks and each chunk
        embedded. The chunks and their embeddings are stored
        in Qdrant for semantic search.

    Example:
        document = Document(
            user_id=user_uuid,
            name="annual_report_2024.pdf",
            content_raw="Full text content of the PDF...",
            type="pdf"
        )
    """

    # Table name in PostgreSQL
    __tablename__ = "documents"

    # Primary key using UUID for global uniqueness
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the document"
    )

    # Foreign key to User table
    # Indexed for fast lookup of user's documents
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the User who owns this document"
    )

    # Document name/title
    # May be the original filename or a user-provided title
    name = Column(
        String(255),
        nullable=False,
        doc="Document name or title"
    )

    # Raw document content or file path
    # For small files, may contain full text content
    # For large files, may contain path to file storage
    content_raw = Column(
        Text,
        nullable=False,
        doc="Raw content or file path to the document data"
    )

    # Document type/format
    # Common values: pdf, txt, md, doc, docx, html
    # Used to determine processing and chunking strategy
    type = Column(
        String(20),
        nullable=False,
        doc="Document type or format (pdf, txt, md, etc.)"
    )

    # Flag indicating if document has been embedded
    # Set to True after successful embedding in Qdrant
    is_embedded = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the document has been embedded in Qdrant"
    )

    # Document upload timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the document was uploaded"
    )

    # Relationship to User
    user = relationship(
        "User",
        back_populates="documents",
        doc="The User who owns this document"
    )

    def __repr__(self) -> str:
        """
        String representation of the Document object.

        Returns:
            String representation showing name and type.
        """
        return f"<Document(name={self.name}, type={self.type})>"