"""
Context Service Module

Handles conversation context management:
- Token counting
- Conversation compression (summarization)
- Auto-compression threshold

This allows long conversations to be summarized while preserving key information.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from app.schemas.message import MessageCreate
from app.core.config import settings


CONTEXT_CONFIG = {
    "max_tokens": 1000,
    "keep_last_messages": 10,
    "max_messages": 20,
    "chars_per_token": 4,
    "summary_max_chars": 4000,
}


class ContextService:
    """
    Service for managing conversation context and compression.
    """

    def get_token_count(self, messages) -> int:
        """
        Estimate token count from a list of messages.

        Args:
            messages: List of message objects with content attribute

        Returns:
            Estimated token count
        """
        total_chars = sum(len(m.content or "") for m in messages)
        return total_chars // CONTEXT_CONFIG["chars_per_token"]

    def should_compress(self, conversation) -> bool:
        """
        Check if conversation should be compressed.

        Args:
            conversation: Conversation object with messages

        Returns:
            True if compression is recommended
        """
        token_count = self.get_token_count(conversation.messages)
        return token_count > CONTEXT_CONFIG["max_tokens"]

    def compress_conversation(
        self,
        db: Session,
        conversation,
        keep_last: Optional[int] = None
    ) -> Optional[str]:
        """
        Compress conversation by summarizing old messages (sync wrapper).
        Use compress_conversation_async for async contexts.
        """
        import asyncio
        return asyncio.run(self.compress_conversation_async(db, conversation, keep_last))

    async def compress_conversation_async(
        self,
        db: Session,
        conversation,
        keep_last: Optional[int] = None
    ) -> Optional[str]:
        """
        Compress conversation by summarizing old messages.

        Keeps the last N messages and summarizes the rest.
        Old messages STAY in DB but won't be included in messages_history.
        Summary is returned for use in LLM context.

        Args:
            db: Database session
            conversation: Conversation object with messages
            keep_last: Number of recent messages to keep (default from config)

        Returns:
            Summary text if compression was performed, None otherwise
        """
        from app.services.llm import ChatService
        from app.core.config import settings

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

        summary_prompt = f"""Summarize this conversation briefly. Keep:
- User preferences and important facts about the user
- Topics discussed
- Any conclusions or decisions made
- Important context for continuing the conversation

Conversation to summarize:
{summary_text[:CONTEXT_CONFIG['summary_max_chars']]}

Provide a concise summary in 2-3 sentences max."""

        llm = ChatService(
            base_url=settings.OLLAMA_CLOUD_HOST,
            api_key=settings.OLLAMA_API_KEY
        )
        try:
            response = await llm.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": summary_prompt}]
            )
            summary = response.get("message", {}).get("content", "")
        except Exception:
            summary = f"Previous context: {len(messages_to_summarize)} messages about various topics."
        finally:
            await llm.close()

        summary_file = "/home/projects/tower_project/prompt/context_summary.md"
        try:
            with open(summary_file, "r") as f:
                content = f.read()
            header = content.split("<!-- Summary will be injected here -->")[0]
            footer = content.split("<!-- Summary will be injected here -->")[1] if "<!-- Summary will be injected here -->" in content else ""
            with open(summary_file, "w") as f:
                f.write(f"{header}<!-- Summary will be injected here -->{footer}\n[{datetime.utcnow().isoformat()}] {summary}")
        except Exception:
            pass

        return summary

    def get_context_info(self, conversation) -> dict:
        """
        Get context information for a conversation.

        Args:
            conversation: Conversation object with messages

        Returns:
            Dict with token count, message count, and compression recommendation
        """
        token_count = self.get_token_count(conversation.messages)
        message_count = len(conversation.messages)

        return {
            "tokens": token_count,
            "messages": message_count,
            "should_compress": self.should_compress(conversation),
            "max_tokens": CONTEXT_CONFIG["max_tokens"],
            "keep_last": CONTEXT_CONFIG["keep_last_messages"],
        }
