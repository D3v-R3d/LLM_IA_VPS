"""
Context Builder

Centralizes all context construction in ONE place.
Builds system messages, manages compression, aggregates tools.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.prompt_service import PromptService
from app.services.context_service import ContextService, CONTEXT_CONFIG
from app.services.memory_service import MemoryService, MemoryContext
from app.services.agent_tools import get_tool_definitions, get_registry
from app.services.agent_core.intent_classifier import select_tools_for_message

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context for agent execution."""
    tools: List[Dict[str, Any]] = field(default_factory=list)
    system_message: Optional[Dict[str, str]] = None
    memory: Optional[str] = None
    user_preferences: Optional[Dict[str, str]] = None
    messages_history: List[Dict] = field(default_factory=list)


class ContextBuilder:
    """
    Centralized context building.

    ALL context construction happens in ONE place:
    - System message building
    - Memory retrieval (tiered: short-term, long-term, summary)
    - Tool aggregation with intent-based shortlisting
    - Compression checks
    """

    def __init__(
        self,
        compression_service: Optional[ContextService] = None,
        prompt_service: Optional[PromptService] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self._compression = compression_service or ContextService()
        self._prompt = prompt_service or PromptService()
        self._memory = memory_service or MemoryService()
        self._registry = get_registry()
        self._all_tool_defs = get_tool_definitions()

    async def build(
        self,
        conversation,
        user_id: int,
        user_message: str = "",
    ) -> AgentContext:
        """
        Build complete agent context from conversation.

        Args:
            conversation: Conversation model instance
            user_id: User ID
            user_message: Current user message for intent-based tool shortlisting

        Returns:
            AgentContext with tools, system_message, etc.
        """
        messages = getattr(conversation, "messages", []) if conversation else []
        memory_ctx = self._memory.build_context(messages, user_message)

        return AgentContext(
            tools=self._select_tools(user_message),
            system_message=None,
            memory=memory_ctx.summary,
            user_preferences=None,
            messages_history=memory_ctx.short_term + memory_ctx.long_term,
        )

    async def build_for_agent(
        self,
        conversation,
        user_id: int,
        user_preferences: Dict[str, str],
        user_message: str = "",
    ) -> Dict[str, Any]:
        """
        Build context dict for agent execution.

        Args:
            conversation: Conversation model instance
            user_id: User ID
            user_preferences: User preferences dict
            user_message: Current user message for intent-based tool shortlisting

        Returns dict with keys:
        - tools: List of tool definitions
        - system_message: System message dict
        - memory: Memory summary if available
        - messages_history: Filtered message history
        """
        tools = self._select_tools(user_message)

        # Tiered memory
        messages = getattr(conversation, "messages", []) if conversation else []
        summary = self._prompt.get_context_summary()
        memory_ctx = self._memory.build_context(messages, user_message, summary=summary)

        system_message = self._prompt.get_system_message(
            user_preferences=user_preferences
        )

        # Build message history: summary (if any) + long-term + short-term
        history = list(memory_ctx.long_term)
        history.extend(memory_ctx.short_term)

        if summary:
            history.insert(0, {"role": "system", "content": f"Résumé de la conversation précédente: {summary}"})

        logger.info(
            f"ContextBuilder: {len(tools)} tools, "
            f"{len(history)} history ({len(memory_ctx.short_term)} short, "
            f"{len(memory_ctx.long_term)} long), "
            f"summary={'yes' if summary else 'no'}"
        )

        return {
            "tools": tools,
            "system_message": system_message,
            "memory": summary,
            "user_preferences": user_preferences,
            "messages_history": history,
        }

    def _select_tools(self, user_message: str) -> List[Dict[str, Any]]:
        """Select tools based on user message intent."""
        if not user_message:
            return self._all_tool_defs

        tool_names = select_tools_for_message(user_message)

        # 0 tools is valid for conversation-only messages — don't fallback
        if not tool_names:
            return []

        selected = self._registry.get_definitions_by_names(tool_names)

        logger.info(f"Intent tools ({len(selected)}): {tool_names}")
        return selected

    def should_compress(self, conversation) -> bool:
        """Check if conversation should be compressed."""
        return self._compression.should_compress(conversation)

    async def compress_conversation_async(self, db, conversation) -> Optional[str]:
        """Trigger async compression if needed."""
        return await self._compression.compress_conversation_async(db, conversation)

    def get_system_message(self, user_preferences: Dict[str, str]) -> Dict[str, str]:
        """Get system message with injects."""
        return self._prompt.get_system_message(user_preferences=user_preferences)

    def get_token_count(self, messages) -> int:
        """Get estimated token count."""
        return self._compression.get_token_count(messages)


def get_context_builder() -> ContextBuilder:
    """Get or create global ContextBuilder instance."""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder


_context_builder: Optional[ContextBuilder] = None