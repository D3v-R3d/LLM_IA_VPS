"""
Context Compression Service

Handles conversation compression (summarization).
Prompts loaded from prompt/generate/
Files injected to prompt/inject/
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

CONTEXT_CONFIG = {
    "max_tokens": 100000,
    "keep_last_messages": 20,
    "max_messages": 20,
    "chars_per_token": 3.5,
    "summary_max_chars": 8000,
}


class ContextCompressionService:
    """Service for compressing conversation context."""

    def get_token_count(self, messages) -> int:
        """Estimate token count from messages."""
        total_chars = sum(len(m.content or "") for m in messages)
        return total_chars // CONTEXT_CONFIG["chars_per_token"]

    def should_compress(self, conversation) -> bool:
        """Check if conversation should be compressed."""
        token_count = self.get_token_count(conversation.messages)
        return token_count > CONTEXT_CONFIG["max_tokens"]

    async def compress(
        self,
        db: Session,
        conversation,
        keep_last: Optional[int] = None
    ) -> Optional[str]:
        """Compress conversation by summarizing old messages."""
        from app.services.llm.provider_factory import provider_factory

        if keep_last is None:
            keep_last = CONTEXT_CONFIG["keep_last_messages"]

        if not conversation or len(conversation.messages) <= keep_last:
            return None

        messages_to_summarize = conversation.messages[:-keep_last]

        summary_text = "\n".join([
            f"{m.role}: {m.content}" for m in messages_to_summarize
            if m.content and m.content.strip()
        ])

        if not summary_text:
            return None

        summarize_prompt_template = PromptService.get_summarize_prompt()
        summary_prompt = summarize_prompt_template.format(
            SUMMARY_TEXT=summary_text[:CONTEXT_CONFIG['summary_max_chars']]
        )

        # Get model and provider from user's preferences
        user_id = conversation.user_id if hasattr(conversation, 'user_id') else None
        model_name = "gemma-4-31b-it"
        provider_name = "google"
        
        if user_id and db:
            from app.models.user_model_prefs import UserModelPrefs
            user_prefs = db.query(UserModelPrefs).filter(UserModelPrefs.user_id == user_id).first()
            if user_prefs:
                model_name = user_prefs.model or "gemma-4-31b-it"
                provider_name = user_prefs.provider or "google"
        
        provider = provider_factory.get_provider(provider_name)
        summary = ""
        try:
            response = await provider.chat(
                model=model_name,
                messages=[{"role": "user", "content": summary_prompt}]
            )
            summary = response.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Context compression error: {e}")
            summary = f"Previous context: {len(messages_to_summarize)} messages about various topics."

        PromptService.write_context_summary(summary)

        return summary

    async def compress_conversation_async(self, db: Session, conversation, keep_last: Optional[int] = None) -> Optional[str]:
        """Alias for compress() for backward compatibility."""
        return await self.compress(db, conversation, keep_last)

    def get_context_info(self, conversation) -> dict:
        """Get context information for a conversation."""
        token_count = self.get_token_count(conversation.messages)
        message_count = len(conversation.messages)

        return {
            "tokens": token_count,
            "messages": message_count,
            "should_compress": self.should_compress(conversation),
            "max_tokens": CONTEXT_CONFIG["max_tokens"],
            "keep_last": CONTEXT_CONFIG["keep_last_messages"],
        }


compression_service = ContextCompressionService()
