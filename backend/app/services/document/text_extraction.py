"""
Text Extraction Service

Extracts text content from various document formats:
- Plain text (.txt)
- Markdown (.md)
- PDF (.pdf)
- HTML (.html)
"""

import re
from typing import Optional
from pathlib import Path


class TextExtractionService:
    """
    Service for extracting text from various document formats.

    This service handles format detection and text extraction.
    OCR is handled separately by OCRService.
    """

    def extract(self, content: str, file_type: Optional[str] = None) -> str:
        """
        Extract text from content based on file type.

        Args:
            content: Raw content or file path
            file_type: File extension (txt, md, pdf, html)

        Returns:
            Extracted text content
        """
        if not content:
            return ""

        if file_type is None:
            file_type = self._detect_type(content)

        if file_type in ("txt", "md"):
            return self._extract_plain_text(content)
        elif file_type == "html":
            return self._extract_html(content)
        elif file_type == "pdf":
            return self._extract_pdf(content)
        else:
            return content

    def _detect_type(self, content: str) -> str:
        """Detect file type from content or filename."""
        if content.startswith("<!DOCTYPE") or content.startswith("<html"):
            return "html"
        if content.startswith("%PDF"):
            return "pdf"
        return "txt"

    def _extract_plain_text(self, content: str) -> str:
        """Extract plain text with basic cleaning."""
        text = content.strip()
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _extract_html(self, content: str) -> str:
        """Extract text from HTML by removing tags."""
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_pdf(self, content: str) -> str:
        """
        Extract text from PDF.

        Note: This is a placeholder. For production, use:
        - PyPDF2 for simple PDFs
        - pdfplumber for better extraction
        - OCR (OCRService) for scanned PDFs
        """
        return content