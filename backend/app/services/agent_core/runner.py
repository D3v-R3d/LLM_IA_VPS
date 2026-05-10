"""
Agent Runner - Thin Wrapper to AgentOrchestrator

This file now serves as a thin wrapper that redirects all requests
to the AgentOrchestrator. Legacy execution logic has been removed.

FEATURE FLAG:
- USE_AGENT_ORCHESTRATOR=true → uses AgentOrchestrator (REQUIRED)
- USE_AGENT_ORCHESTRATOR=false → raises RuntimeError
"""

import logging
import uuid
from typing import List, Dict, Optional

from app.services.agent_core.config import AgentConfig
from app.services.agent_core.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Thin wrapper that routes all requests to AgentOrchestrator.
    
    Legacy execution logic has been removed. All requests now go through
    AgentOrchestrator which provides:
    - Idempotency
    - Loop detection
    - Smart context compression
    - Retry stability
    - LLM logging
    - Budget management
    """

    def __init__(
        self,
        llm=None,
        tool_executor=None,
        max_steps: int = 3,
        max_context: int = 30,
        max_tool_chars: int = 1200,
        llm_timeout: int = 200,
        budgets: Optional[Dict[str, int]] = None,
        provider_factory=None,
    ):
        self._config = AgentConfig.from_env()
        self._config.validate()

        self._orchestrator = AgentOrchestrator(config=self._config)

        logger.info("AgentOrchestrator enabled - legacy runner removed")

    async def run(
        self,
        user_message: str,
        messages_history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        chat_id: str,
        user_id: Optional[str] = None,
        model: str = None,
        provider_name: Optional[str] = None,
        db_session=None,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> str:
        """Route all requests to AgentOrchestrator."""
        if self._orchestrator is None:
            raise RuntimeError(
                "AgentOrchestrator is required. "
                "Set USE_AGENT_ORCHESTRATOR=true in environment."
            )

        return await self._orchestrator.run(
            user_message=user_message,
            messages_history=messages_history,
            system_prompt=system_prompt,
            chat_id=chat_id,
            user_id=user_id,
            model=model,
            provider_name=provider_name,
            db_session=db_session,
            conversation_id=conversation_id,
        )