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
from app.services.agent_tools import get_tool_definitions

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context for agent execution."""
    tools: List[Dict[str, Any]] = field(default_factory=list)
    system_message: Optional[Dict[str, str]] = None
    memory: Optional[str] = None
    user_preferences: Optional[Dict[str, str]] = None


class ContextBuilder:
    """
    Centralized context building.

    ALL context construction happens in ONE place:
    - System message building
    - Memory retrieval
    - Tool aggregation
    - Compression checks
    """

    def __init__(
        self,
        compression_service: Optional[ContextService] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self._compression = compression_service or ContextService()
        self._prompt = prompt_service or PromptService()
        self._agent_tools = get_tool_definitions()

    async def build(
        self,
        conversation,
        user_id: int,
    ) -> AgentContext:
        """
        Build complete agent context from conversation.

        Args:
            conversation: Conversation model instance
            user_id: User ID

        Returns:
            AgentContext with tools, system_message, etc.
        """
        return AgentContext(
            tools=self._agent_tools,
            system_message=None,
            memory=None,
            user_preferences=None,
        )

    async def build_for_agent(
        self,
        conversation,
        user_id: int,
        user_preferences: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Build context dict for agent execution.

        Returns dict with keys:
        - tools: List of tool definitions
        - system_message: System message dict
        - memory: Memory summary if available
        """
        tools = self._get_tools()

        system_message = self._prompt.get_system_message(
            user_preferences=user_preferences
        )

        return {
            "tools": tools,
            "system_message": system_message,
            "memory": None,
            "user_preferences": user_preferences,
        }

    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get combined tool list from services."""
        return self._agent_tools

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