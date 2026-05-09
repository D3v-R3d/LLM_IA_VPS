"""
Chat Orchestrator

Central coordination layer for chat messages.
Handles session resolution, context building, agent execution, and response saving.
"""

import asyncio
import logging
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
                prefs["model"] = user.model_prefs.model
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