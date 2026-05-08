"""
Text Handler for Telegram Regular Messages

Handles non-command text messages by dispatching to the orchestrator.
"""

import logging
from typing import Optional

from app.services.telegram.handlers.base import BaseHandler, TelegramUpdate, HandlerContext

logger = logging.getLogger(__name__)


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
        from app.services.llm import ChatService
        from app.core.config import settings

        logger = logging.getLogger(__name__)
        logger.info(f"TextHandler: chat_id={update.chat_id}, text={update.text[:50] if update.text else 'None'}...")

        try:
            is_linked, user = await _require_linked_account(update.chat_id, context, "Chatting")
            if not is_linked:
                return None

            if self._orchestrator is None:
                from app.services.agent_tools import get_registry
                registry = get_registry()
                llm = ChatService(base_url=settings.OLLAMA_CLOUD_HOST, api_key=settings.OLLAMA_API_KEY)
                tool_executor = ToolExecutor(registry=registry)
                agent_runner = AgentRunner(llm=llm, tool_executor=tool_executor)
                context_builder = ContextBuilder()
                self._orchestrator = ChatOrchestrator(
                    conversation_service=context.conversation_service,
                    message_service=context.message_service,
                    user_service=context.user_service,
                    telegram_service=context.telegram_service,
                    agent_runner=agent_runner,
                    context_builder=context_builder,
                )

            response = await self._orchestrator.route_message(
                chat_id=update.chat_id,
                user_id=user.id,
                text=update.text,
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
    from app.services.synology import SynologyClient, SynologyAuth, FileStation
    from app.services.telegram.handlers.commands import _format_size

    folder_path = data[3:].strip()
    if not folder_path.startswith("/"):
        folder_path = f"/{folder_path}"

    try:
        client = SynologyClient()
        auth = SynologyAuth(client)
        auth.login()
        nas = FileStation(client)

        result = nas.list_folders(folder_path)
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
    model_id = data[13:]

    is_linked, user = await _require_linked_account(chat_id, context)
    if not is_linked:
        await context.telegram_service.answer_callback_query(query_id, text="Account not linked", show_alert=True)
        return None

    success = context.user_service.set_preference(context.db, user.id, "model", model_id)

    if success:
        await context.telegram_service.answer_callback_query(
            query_id,
            text=f"✓ Switched to {model_id}",
            show_alert=True
        )
        await context.telegram_service.send_message(
            chat_id,
            f"✓ Model switched to `{model_id}`\nThis will be used for your next messages."
        )
    else:
        await context.telegram_service.answer_callback_query(query_id, text="Failed to save", show_alert=True)

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