"""
Chat Orchestrator

Central coordination layer for chat messages.
Handles session resolution, context building, agent execution, and response saving.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ChatRequest:
    """Request to process a chat message."""
    chat_id: str
    user_id: Optional[int]
    text: str
    session_id: Optional[str] = None


@dataclass
class ChatResponse:
    """Response from processing a chat message."""
    text: str
    success: bool = True


class ChatOrchestrator:
    """
    Central coordinator for chat processing.

    Orchestrates:
    - Session resolution
    - Context building
    - Agent execution
    - Response saving
    - Telegram sending
    """

    def __init__(
        self,
        conversation_service,
        message_service,
        user_service,
        telegram_service,
        agent_runner,
        context_builder,
    ):
        self._conversation = conversation_service
        self._message = message_service
        self._user = user_service
        self._telegram = telegram_service
        self._agent = agent_runner
        self._context = context_builder

    async def route_message(self, chat_id: str, user_id: Optional[int], text: str) -> Optional[str]:
        """
        Process a chat message and return response text.

        Returns response text to send via Telegram, or None for no response.
        """
        logger.info(f"ChatOrchestrator: chat_id={chat_id}, user_id={user_id}, text={text[:50]}...")

        from app.models.database import get_db
        db_gen = get_db()
        db = next(db_gen)

        try:
            user = self._user.get_by_telegram_chat_id(db, chat_id)
            if not user:
                logger.warning(f"No linked user for chat_id={chat_id}")
                await self._telegram.send_message(
                    chat_id,
                    "❌ Account not linked. Use /link <email> to link your account."
                )
                return None

            session = await self._resolve_session(db, user, chat_id)
            if not session:
                return None

            conversation = session

            prefs = {}
            if user.model_prefs:
                if user.model_prefs.model:
                    prefs["model"] = user.model_prefs.model
                if user.model_prefs.provider:
                    prefs["provider"] = user.model_prefs.provider
                if user.model_prefs.current_session:
                    prefs["current_session"] = user.model_prefs.current_session

            should_compress = conversation and len(conversation.messages) > 30
            if should_compress:
                await self._telegram.send_chat_action(chat_id, "typing")
                asyncio.create_task(
                    self._context.compress_conversation_async(db, conversation)
                )

            await self._telegram.send_chat_action(chat_id, "typing")

            from app.schemas.message import MessageCreate

            user_msg = self._message.create(
                db=db,
                user_id=user.id,
                message_data=MessageCreate(
                    conversation_id=conversation.id,
                    role="user",
                    content=text
                )
            )

            system_message = self._context.get_system_message(
                user_preferences=prefs
            )

            agent_context = await self._context.build(
                conversation=conversation,
                user_id=user.id,
                user_message=text
            )

            response = await self._agent.run(
                user_message=text,
                messages_history=agent_context.messages_history,
                system_prompt=system_message["content"],
                tools=agent_context.tools,
                chat_id=chat_id,
                user_id=str(user.id),
                model=prefs.get("model"),
                provider_name=prefs.get("provider"),
                db_session=db,
                conversation_id=conversation.id,
            )

            logger.info(f"Synthesis check - provider: {prefs.get('provider')}, model: {prefs.get('model')}, response_len: {len(response)}")
            if prefs.get("provider") or prefs.get("model"):
                logger.info("Calling synthesize response...")
                response = await self._synthesize_response(
                    response, prefs.get("provider"), prefs.get("model")
                )
                logger.info(f"Synthesis result len: {len(response)}")

            self._message.create(
                db=db,
                user_id=user.id,
                message_data=MessageCreate(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response
                )
            )

            self._conversation.update_timestamp(db, conversation.id)

            return response

        except Exception as e:
            logger.exception(f"ChatOrchestrator error: {e}")
            return "I'm thinking... Please try again in a moment."
        finally:
            db.close()

    async def _synthesize_response(
        self,
        response: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """Synthesize response using LLM for natural language."""
        if not response or len(response) < 100:
            return response

        from app.services.llm.provider_factory import provider_factory
        from app.core.config import settings

        provider = provider_name or settings.LLM_PROVIDER
        llm_provider = provider_factory.get_provider(provider)

        synthesis_system = self._load_synthesis_prompt()
        logger.info(f"Loaded synthesis prompt length: {len(synthesis_system)}")

        synthesis_prompt = [
            {"role": "system", "content": synthesis_system},
            {"role": "user", "content": f"Réponse à synthétiser:\n{response}"}
        ]

        try:
            if provider == "openrouter":
                llm_response = await llm_provider.chat(
                    model=model or "openai/gpt-4",
                    messages=synthesis_prompt,
                    options={"max_tokens": 5000}
                )
            else:
                llm_response = await llm_provider.chat(synthesis_prompt, max_tokens=500)

            if llm_response and llm_response.get("content"):
                return llm_response["content"]
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")

        return response

    def _load_synthesis_prompt(self) -> str:
        """Load synthesis prompt from file."""
        prompt_dir = os.environ.get("PROMPT_DIR", "/home/projects/tower_project")
        prompt_file = os.path.join(prompt_dir, "inject", "synthesis.md")

        try:
            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Could not load synthesis prompt: {e}")

        return (
            "Tu es un assistant expert en communication. "
            "Synthétise les résultats des outils en une réponse claire, concise et naturelle en français. "
            "Conserve les mêmes faits et chiffres, reformule de manière naturelle."
        )

    async def _resolve_session(self, db, user, chat_id: str):
        """Resolve or create a session for the user."""
        current_session = None
        if user.model_prefs:
            current_session = user.model_prefs.current_session

        if current_session:
            conversation = self._conversation.get_telegram_session(db, user.id, current_session)
            if conversation:
                return conversation

        conversation = self._conversation.get_by_telegram_chat_id(db, chat_id)
        if not conversation:
            conversation = self._conversation.create_telegram_session(db, user.id, chat_id)

        return conversation