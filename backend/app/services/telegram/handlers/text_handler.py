"""
Text Handler for Telegram Regular Messages

Handles non-command text messages by dispatching to the orchestrator.
"""

import logging
from typing import Optional

from app.services.telegram.handlers.base import BaseHandler, TelegramUpdate, HandlerContext
from app.observability.event_types import EventType

logger = logging.getLogger(__name__)

# Global cached instances
_cached_orchestrator = None
_cached_registry = None
_cached_llm = None


def _get_cached_orchestrator(context: HandlerContext):
    """Get or create cached orchestrator instance."""
    global _cached_orchestrator, _cached_registry, _cached_llm
    
    if _cached_orchestrator is not None:
        return _cached_orchestrator
    
    from app.services.agent_tools import get_registry
    from app.services.agent_core import ToolExecutor
    from app.services.llm.provider_factory import provider_factory
    from app.core.config import settings
    from app.services.agent_core.runner import AgentRunner
    from app.services.agent_core.context_builder import ContextBuilder
    from app.orchestration.chat_orchestrator import ChatOrchestrator
    
    _cached_registry = get_registry()
    _cached_llm = provider_factory.get_provider(settings.LLM_PROVIDER)
    tool_executor = ToolExecutor(registry=_cached_registry)
    agent_runner = AgentRunner(llm=_cached_llm, tool_executor=tool_executor, provider_factory=provider_factory)
    context_builder = ContextBuilder()
    
    _cached_orchestrator = ChatOrchestrator(
        conversation_service=context.conversation_service,
        message_service=context.message_service,
        user_service=context.user_service,
        telegram_service=context.telegram_service,
        agent_runner=agent_runner,
        context_builder=context_builder,
    )
    
    logger.info("TextHandler: orchestrator cached")
    return _cached_orchestrator


class TextHandler(BaseHandler):
    """
    Handles regular text messages (non-commands).

    Dispatches to ChatOrchestrator for business logic.
    """

    def __init__(self, orchestrator=None):
        self._orchestrator = orchestrator

    async def can_handle(self, update: TelegramUpdate) -> bool:
        """Check if this is a regular text message (not a command)."""
        return update.text is not None and update.command is None

    async def handle(self, update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
        """Handle the text message - delegate to ChatOrchestrator."""
        from app.orchestration.chat_orchestrator import ChatOrchestrator
        from app.services.agent_core.runner import AgentRunner
        from app.services.agent_core.context_builder import ContextBuilder
        from app.services.agent_core import ToolExecutor
        from app.services.llm.provider_factory import provider_factory
        from app.core.config import settings

        logger = logging.getLogger(__name__)
        logger.info(f"TextHandler: chat_id={update.chat_id}, text={update.text[:50] if update.text else 'None'}...")

        try:
            is_linked, user = await _require_linked_account(update.chat_id, context, "Chatting")
            if not is_linked:
                if context.event_logger:
                    await context.event_logger.emit_async(
                        event_type=EventType.ACCOUNT_NOT_LINKED,
                        event_name="account_not_linked",
                        payload={"chat_id": update.chat_id, "action": "Chatting"},
                    )
                return None

            if context.event_logger:
                context.event_logger.set_user_id(str(user.id))
                await context.event_logger.emit_async(
                    event_type=EventType.USER_RESOLVED,
                    event_name="user_resolved",
                    payload={"user_id": str(user.id), "username": getattr(user, 'username', None) or getattr(user, 'email', None)},
                )

            self._orchestrator = _get_cached_orchestrator(context)

            response = await self._orchestrator.route_message(
                chat_id=update.chat_id,
                user_id=user.id,
                text=update.text,
                run_id=context.run_id,
                event_logger=context.event_logger,
            )

            return response

        except Exception as e:
            logger.exception(f"TextHandler error: {e}")
            return "Je réfléchis... Réessayez dans un moment."


class CallbackQueryHandler(BaseHandler):
    """Handles Telegram callback queries (inline button clicks)."""

    async def can_handle(self, update: TelegramUpdate) -> bool:
        """Check if this is a callback query."""
        return "callback_query" in update.raw

    async def handle(self, update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
        """Handle the callback query."""
        callback_query = update.raw.get("callback_query", {})
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        chat_id = update.chat_id

        logger.info(f"Callback query: data={data}, chat_id={chat_id}")

        if data.startswith("/ls"):
            return await _handle_ls_callback(data, chat_id, context)

        if data.startswith("model_switch:"):
            return await _handle_model_switch_callback(data, query_id, chat_id, context)

        if data.startswith("conv_"):
            conversation_id = data[5:]
            await context.telegram_service.answer_callback_query(
                query_id,
                text="Opening conversation...",
                show_alert=False
            )
            return None

        await context.telegram_service.answer_callback_query(
            query_id,
            text="Unknown action",
            show_alert=True
        )
        return None


async def _handle_ls_callback(data: str, chat_id: str, context: HandlerContext) -> Optional[str]:
    """Handle /ls callback from inline keyboard."""
    from app.services.synology_service import SynologyService
    from app.services.telegram.handlers.commands import _format_size

    folder_path = data[3:].strip()
    if not folder_path.startswith("/"):
        folder_path = f"/{folder_path}"

    try:
        service = SynologyService.get_instance()
        result = service.list_folder(folder_path)
        files = result.get("data", {}).get("files", [])

        if not files:
            await context.telegram_service.send_message(chat_id, f"Dossier vide: {folder_path}")
            return None

        text_lines = [f"📂 *Contenu de {folder_path}:*\n"]
        keyboard = []

        for f in files[:20]:
            name = f["name"]
            if f.get("isdir"):
                subpath = f"{folder_path}/{name}" if folder_path != "/" else f"/{name}"
                keyboard.append([{"text": f"📁 {name}", "callback_data": f"/ls {subpath}"}])
            else:
                size = f.get("size", 0)
                if size:
                    size_str = _format_size(size)
                    text_lines.append(f"📄 {name} ({size_str})")
                else:
                    text_lines.append(f"📄 {name}")

        if len(files) > 20:
            text_lines.append(f"\n... et {len(files) - 20} autres fichiers")

        if keyboard:
            reply_markup = {"inline_keyboard": keyboard}
            await context.telegram_service.send_message(
                chat_id,
                "\n".join(text_lines),
                reply_markup=reply_markup
            )
        else:
            await context.telegram_service.send_message(chat_id, "\n".join(text_lines))

    except Exception as e:
        await context.telegram_service.send_message(chat_id, f"❌ Erreur: {str(e)}")

    return None


async def _handle_model_switch_callback(
    data: str, query_id: str, chat_id: str, context: HandlerContext
) -> Optional[str]:
    """Handle model_switch callback from inline keyboard."""
    payload = data[13:]
    parts = payload.split("||", 1)
    if len(parts) == 2:
        model_id = parts[1]
        provider = parts[0]
    else:
        model_id = payload
        provider = "ollama"

    is_linked, user = await _require_linked_account(chat_id, context)
    if not is_linked:
        await context.telegram_service.answer_callback_query(query_id, text="Account not linked", show_alert=True)
        return None

    from app.models.user_model_prefs import UserModelPrefs

    if user.model_prefs:
        user.model_prefs.model = model_id
        user.model_prefs.provider = provider
    else:
        prefs = UserModelPrefs(
            user_id=user.id,
            provider=provider,
            model=model_id,
            is_local=(provider == "ollama")
        )
        context.db.add(prefs)

    context.db.commit()

    await context.telegram_service.answer_callback_query(
        query_id,
        text=f"✓ Switched to {model_id}",
        show_alert=True
    )
    await context.telegram_service.send_message(
        chat_id,
        f"✓ Model switched to `{model_id}` ({provider})\nThis will be used for your next messages."
    )

    return None


async def _require_linked_account(chat_id: str, context: HandlerContext, action: str = "This action"):
    """Check if user is linked, send message if not. Returns (is_linked, user)."""
    user = context.user_service.get_by_telegram_chat_id(context.db, chat_id)

    if not user:
        await context.telegram_service.send_message(
            chat_id,
            f"❌ {action} requires linking your account first.\n\nUse /link <email> to link your Tower account."
        )
        return False, None

    return True, user