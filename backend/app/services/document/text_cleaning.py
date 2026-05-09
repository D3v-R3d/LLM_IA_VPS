"""
Text Cleaning Service

Cleans and normalizes text content:
- Removes special characters
- Normalizes whitespace
- Fixes encoding issues
"""

import re
import unicodedata
from typing import List


class TextCleaningService:
    """
    Service for cleaning and normalizing text content.

    Prepares text for chunking and embedding by removing
    noise and normalizing format.
    """

    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        Clean multiple texts.

        Args:
            texts: List of raw texts

        Returns:
            List of cleaned texts
        """
        return [self.clean(text) for text in texts]

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters."""
        return unicodedata.normalize("NFKC", text)

    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters except newlines and tabs."""
        return "".join(
            char for char in text
            if char == "\n" or char == "\t" or not unicodedata.category(char).startswith("C")
        )

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize spaces and tabs."""
        text = re.sub(r'[ \t]+', ' ', text)
        return text

    def _remove_extra_newlines(self, text: str) -> str:
        """Remove excessive newlines."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _remove_javascript_artifacts(self, text: str) -> str:
        """Remove JavaScript artifacts while preserving readable content."""
        import re

        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<noscript[^>]*>.*?</noscript>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
        text = re.sub(r'<svg[^>]*>.*?</svg>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<path\s+[^>]+>', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)

        text = re.sub(r'var\s+\w+\s*=\s*["\'][^"\']*["\']', ' ', text)
        text = re.sub(r'var\s+\w+\s*=\s*[^;]{0,200};', ' ', text)
        text = re.sub(r'function\s+\w+\s*\([^)]*\)', ' ', text)
        text = re.sub(r'addeventlistener\s*\([^;)]+;', ' ', text)

        text = re.sub(r'__md_\w+', ' ', text)
        text = re.sub(r'JSON\.parse', ' ', text)
        text = re.sub(r'localStorage', ' ', text)
        text = re.sub(r'matchMedia', ' ', text)
        text = re.sub(r'querySelector', ' ', text)
        text = re.sub(r'dispatchEvent', ' ', text)
        text = re.sub(r'addEventListener', ' ', text)
        text = re.sub(r'classList', ' ', text)

        text = re.sub(r'=>\s*\{[^}]+\}', ' ', text)
        text = re.sub(r'\[\^[^\]]+\]', ' ', text)
        text = re.sub(r'\(\w+\s*,\s*\w+\)\s*=>', ' ', text)
        text = re.sub(r'\.reduce\(\w+,', ' ', text)
        text = re.sub(r'\.getItem\([^)]+\)', ' ', text)
        text = re.sub(r'\.setItem\([^)]+\)', ' ', text)

        text = re.sub(r'data-md-\w+="[^"]*"', ' ', text)
        text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', ' ', text)

        text = re.sub(r'\([^)]*\)\s*\{[^}]{0,300}\}', ' ', text)

        text = re.sub(r'\s+', ' ', text)

        return text

    def clean(self, text: str) -> str:
        """
        Clean text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        text = self._normalize_unicode(text)
        text = self._remove_control_chars(text)
        text = self._remove_javascript_artifacts(text)
        text = self._normalize_whitespace(text)
        text = self._remove_extra_newlines(text)

        return text.strip()

    def truncate(self, text: str, max_length: int = 10000) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum character length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."