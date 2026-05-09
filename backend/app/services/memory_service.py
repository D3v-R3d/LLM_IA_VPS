"""
Memory Service

Tiered memory with semantic retrieval.
Short-term: last N messages (always included)
Long-term: relevant older messages (keyword-matched)
Summary: compressed conversation history
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """Tiered memory context for LLM."""
    short_term: List[Dict] = field(default_factory=list)
    long_term: List[Dict] = field(default_factory=list)
    summary: Optional[str] = None


class MemoryService:
    """
    Tiered memory with keyword-based retrieval.

    Tiers:
    - Short-term: last SHORT_TERM_COUNT messages (always included)
    - Long-term: messages retrieved by keyword matching against user query
    - Summary: compressed old messages (if available)
    """

    SHORT_TERM_COUNT = 10
    LONG_TERM_COUNT = 5
    SUMMARY_THRESHOLD = 50

    def __init__(self, short_term_count: int = None, long_term_count: int = None):
        self._short_term_count = short_term_count or self.SHORT_TERM_COUNT
        self._long_term_count = long_term_count or self.LONG_TERM_COUNT

    def build_context(
        self,
        messages: List,
        user_message: str,
        summary: Optional[str] = None,
    ) -> MemoryContext:
        """
        Build tiered memory context from messages.

        Args:
            messages: All conversation messages (list of objects with .role and .content)
            user_message: Current user message for keyword matching
            summary: Optional compressed summary of old messages

        Returns:
            MemoryContext with short_term, long_term, summary
        """
        if not messages:
            return MemoryContext()

        formatted = self._format_messages(messages)

        # Short-term: always include last N
        short_term = formatted[-self._short_term_count:]

        # Summary
        context_summary = summary if summary else None

        # Long-term: keyword match from older messages
        long_term = []
        older = formatted[:-self._short_term_count]
        if older and user_message:
            long_term = self._keyword_retrieval(older, user_message, self._long_term_count)

        logger.info(
            f"Memory: short_term={len(short_term)}, "
            f"long_term={len(long_term)}, "
            f"summary={'yes' if context_summary else 'no'}"
        )

        return MemoryContext(
            short_term=short_term,
            long_term=long_term,
            summary=context_summary,
        )

    def _keyword_retrieval(
        self,
        messages: List[Dict],
        query: str,
        max_results: int,
    ) -> List[Dict]:
        """
        Retrieve relevant messages by keyword matching.

        Extracts significant keywords from query (3+ chars, not stopwords)
        and finds messages containing them.
        """
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        scored: List[tuple[int, Dict]] = []
        for msg in reversed(messages):
            content = (msg.get("content") or "").lower()
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                scored.append((score, msg))

        # Sort by score descending, take top results
        scored.sort(key=lambda x: x[0], reverse=True)
        return [msg for _, msg in scored[:max_results]]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract significant keywords from text."""
        STOPWORDS = {
            "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet",
            "cette", "ces", "mon", "ton", "son", "ma", "ta", "sa",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "me", "te", "se", "lui", "leur",
            "et", "ou", "mais", "donc", "car", "ni", "or",
            "que", "qui", "quoi", "dont", "ou",
            "a", "au", "aux", "dans", "par", "pour", "sur", "avec", "sans",
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
            "and", "or", "but", "not", "is", "are", "was", "were",
            "i", "you", "he", "she", "it", "we", "they",
            "me", "my", "your", "his", "her", "its", "our", "their",
            "this", "that", "these", "those",
            "peux", "peut", "fait", "faire", "vas",
            "s", "d", "c", "t", "m", "n",
        }

        words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def _format_messages(self, messages: List) -> List[Dict]:
        """Format messages into dict list."""
        result = []
        for m in messages:
            role = getattr(m, "role", None)
            if hasattr(role, "value"):
                role = role.value
            content = getattr(m, "content", None) or ""
            if role and content:
                result.append({"role": str(role), "content": content})
        return result
