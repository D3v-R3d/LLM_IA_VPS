"""
Individual Command Handlers for Telegram

Each handler is a separate function for maintainability.
"""

from typing import Optional
import uuid
import logging

from app.services.telegram.handlers.base import TelegramUpdate, HandlerContext
from app.core.config import settings

logger = logging.getLogger(__name__)


def _format_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


async def handle_start_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /start command."""
    if update.text and update.text.startswith("link_"):
        token = update.text[5:]
        return await _handle_link_token(update.chat_id, token, context)

    text = (
        "*Welcome to Tower Bot!*\n\n"
        "Your AI assistant with NAS access.\n\n"
        "*Commands:*\n"
        "/nas - List NAS shares\n"
        "/ls <folder> - Browse NAS folders\n"
        "/naslogin - Connect to NAS\n"
        "/model - List/switch AI models (/model list, /model switch <id>)\n"
        "/status - Check your account\n"
        "/help - Show this help\n"
    )
    await context.telegram_service.send_message(update.chat_id, text)
    return None


async def handle_help_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /help command."""
    text = (
        "*Tower Bot Help*\n\n"
        "*AI Commands (via chat):*\n"
        "Ask me anything! I have access to:\n"
        "• Web search & fetch URLs\n"
        "• NAS file browsing\n"
        "• Database queries\n"
        "• File operations (read, write, edit)\n"
        "• System commands (bash, docker, git)\n\n"
        "*Direct Commands:*\n"
        "/nas - List all shared folders on NAS\n"
        "/ls <folder> - List files in folder\n"
        "/naslogin - Connect to Synology NAS\n"
        "/status - Check connection status\n"
        "/link <email> - Link your account\n"
        "/unlink - Unlink your account\n"
        "/new - Start new session\n"
        "/reset - Clear conversation\n"
        "/compress - Summarize conversation\n"
        "/sessions - List your sessions\n"
        "/prefs - Show preferences\n"
        "/setpref key=value - Set preference\n"
        "/model - Switch AI model\n\n"
        "*Messaging:*\n"
        "Just type your message to chat with Tower!\n"
        "Example: \"list my nas folders\" or \"search web for python\"\n"
    )
    await context.telegram_service.send_message(update.chat_id, text)
    return None


async def handle_status_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /status command."""
    user = context.user_service.get_by_telegram_chat_id(context.db, update.chat_id)

    if user:
        text = (
            f"*Account Status*\n\n"
            f"✓ Linked to: {user.email}\n"
            f"✓ Name: {user.name}"
        )
    else:
        text = (
            "*Account Status*\n\n"
            "✗ Not linked to any Tower account\n\n"
            "Use /link <email> to link your account."
        )

    await context.telegram_service.send_message(update.chat_id, text)
    return None


async def handle_link_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /link <email> command."""
    if not update.text:
        await context.telegram_service.send_message(
            update.chat_id,
            "Usage: /link <email>\n\nExample: /link user@example.com"
        )
        return None

    success = context.user_service.link_telegram_chat_id_by_email(
        context.db, update.text, update.chat_id
    )

    if success:
        await context.telegram_service.send_notification(
            update.chat_id,
            "Account Linked",
            f"Telegram linked to {update.text}",
            "success"
        )
    else:
        await context.telegram_service.send_message(
            update.chat_id,
            "❌ Link failed. User not found or already linked."
        )

    return None


async def handle_unlink_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /unlink command."""
    success = context.user_service.unlink_telegram_chat_id(context.db, update.chat_id)

    if success:
        await context.telegram_service.send_notification(
            update.chat_id,
            "Account Unlinked",
            "Your Telegram account has been unlinked from Tower.",
            "info"
        )
    else:
        await context.telegram_service.send_message(
            update.chat_id,
            "❌ Unlink failed. No account was linked."
        )

    return None


async def handle_register_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /register command - redirect to web app."""
    await context.telegram_service.send_message(
        update.chat_id,
        "❌ Registration is not available via Telegram.\n\n"
        "Please register via the web app at:\n"
        "https://www.srv1632761.hstgr.cloud\n\n"
        "After registering, use /link <email> to link your account."
    )
    return None


async def handle_setpref_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /setpref key=value command."""
    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    if not update.text or "=" not in update.text:
        await context.telegram_service.send_message(
            update.chat_id,
            "Usage: /setpref key=value\n\nExamples:\n/setpref name=John\n/setpref language=fr\n/setpref style=concise\n/setpref timezone=Europe/Paris"
        )
        return None

    try:
        key, value = update.text.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if not key or not value:
            await context.telegram_service.send_message(
                update.chat_id,
                "❌ Invalid format. Use: /setpref key=value"
            )
            return None

        success = context.user_service.set_preference(context.db, user.id, key, value)

        if success:
            await context.telegram_service.send_notification(
                update.chat_id,
                "Preference Set",
                f"✓ {key} = {value}",
                "success"
            )
        else:
            await context.telegram_service.send_message(
                update.chat_id,
                "❌ Failed to set preference"
            )
    except Exception as e:
        logger.error(f"Error setting preference: {e}")
        await context.telegram_service.send_message(
            update.chat_id,
            "Failed to set preference. Please try again."
        )

    return None


async def handle_prefs_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /prefs command - show user preferences."""
    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    prefs = context.user_service.get_preferences(context.db, user.id)

    if not prefs:
        text = (
            "*Your Preferences*\n\n"
            "No preferences set yet.\n\n"
            "Use /setpref key=value to set preferences.\n\n"
            "Example: /setpref name=John"
        )
    else:
        lines = ["*Your Preferences*\n"]
        for key, value in prefs.items():
            lines.append(f"• {key}: {value}")
        text = "\n".join(lines)

    await context.telegram_service.send_message(update.chat_id, text)
    return None


async def handle_sessions_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /sessions command - list all sessions."""
    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    if not context.conversation_service:
        return None

    sessions = context.conversation_service.get_all_telegram_sessions(context.db, user.id)
    current = user.model_prefs.current_session if user.model_prefs else None

    if not sessions:
        text = "*Your Sessions*\n\nNo sessions yet. Start chatting to create one!"
    else:
        lines = ["*Your Sessions*\n"]
        for s in sessions:
            marker = "✓" if s.telegram_chat_id == current else " "
            lines.append(f"{marker} {s.title} ({s.telegram_chat_id[:8]})")
        text = "\n".join(lines)

    await context.telegram_service.send_message(update.chat_id, text)
    return None


async def handle_new_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /new command - start a new session."""
    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    if not context.conversation_service:
        return None

    session_id = str(uuid.uuid4())
    title = update.text.strip() if update.text and update.text.strip() else f"Session {session_id[:8]}"

    conversation = context.conversation_service.create_telegram_session(
        context.db, user.id, session_id, title
    )
    if not user.model_prefs:
        from app.models.user_model_prefs import UserModelPrefs
        user.model_prefs = UserModelPrefs(user_id=user.id, current_session=session_id)
        context.db.add(user.model_prefs)
    else:
        user.model_prefs.current_session = session_id
    context.db.commit()

    await context.telegram_service.send_notification(
        update.chat_id,
        "New Session Started",
        f"✓ {title}\n\nAll messages will be in this session.",
        "success"
    )
    return None


async def handle_reset_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /reset command - clear current session and start fresh."""
    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    current_session = user.model_prefs.current_session if user.model_prefs else None

    if current_session and context.conversation_service:
        conv = context.conversation_service.get_telegram_session(context.db, user.id, current_session)
        if conv and context.message_service:
            for msg in conv.messages:
                context.message_service.delete(context.db, msg.id)

    if user.model_prefs:
        user.model_prefs.current_session = None
        context.db.commit()

    await context.telegram_service.send_notification(
        update.chat_id,
        "Session Reset",
        "✓ Context cleared. Starting fresh!",
        "info"
    )
    return None


async def handle_compress_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /compress command - summarize and compress conversation history."""
    from app.services.context_service import CONTEXT_CONFIG

    is_linked, user = await _require_linked_account(update.chat_id, context)
    if not is_linked:
        return None

    if not context.conversation_service:
        return None

    current_session = user.model_prefs.current_session if user.model_prefs else None

    if current_session:
        conversation = context.conversation_service.get_telegram_session(context.db, user.id, current_session)
    else:
        conversation = context.conversation_service.get_telegram_conversation(context.db, user.id)

    if not conversation:
        await context.telegram_service.send_message(update.chat_id, "❌ No active session found.")
        return None

    token_count = context.conversation_service.get_token_count(conversation)

    if token_count < 500:
        await context.telegram_service.send_message(
            update.chat_id,
            f"✅ Session is already compact ({token_count} tokens). No compression needed."
        )
        return None

    await context.telegram_service.send_chat_action(update.chat_id, "typing")

    summary = await context.conversation_service.compress_conversation(
        context.db, conversation.id, keep_last=CONTEXT_CONFIG["keep_last_messages"]
    )

    new_count = context.conversation_service.get_token_count(conversation)

    if summary:
        await context.telegram_service.send_notification(
            update.chat_id,
            "Session Compressed",
            f"✓ {token_count} → {new_count} tokens\n\n{summary[:200]}...",
            "success"
        )
    else:
        await context.telegram_service.send_message(
            update.chat_id,
            f"❌ Compression failed or not needed."
        )

    return None


async def handle_nas_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /nas command - list shares on NAS."""
    from app.services.synology_service import SynologyService

    try:
        service = SynologyService.get_instance()
        shares = service.list_shares()
        share_list = shares.get("data", {}).get("shares", [])

        if not share_list:
            await context.telegram_service.send_message(update.chat_id, "Aucun partage trouvé.")
            return None

        lines = ["📁 *Partages NAS:*\n"]
        for s in share_list:
            lines.append(f"• {s['name']} ({s['path']})")

        await context.telegram_service.send_message(update.chat_id, "\n".join(lines))
    except Exception as e:
        await context.telegram_service.send_message(update.chat_id, f"❌ Erreur: {str(e)}")

    return None


async def handle_ls_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /ls command - list files in a NAS folder."""
    from app.services.synology_service import SynologyService

    folder_path = update.text if update.text and update.text.startswith("/") else f"/{update.text or ''}"

    try:
        service = SynologyService.get_instance()
        result = service.list_folder(folder_path)
        files = result.get("data", {}).get("files", [])

        if not files:
            await context.telegram_service.send_message(update.chat_id, f"Dossier vide: {folder_path}")
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
                update.chat_id,
                "\n".join(text_lines),
                reply_markup=reply_markup
            )
        else:
            await context.telegram_service.send_message(update.chat_id, "\n".join(text_lines))

    except Exception as e:
        await context.telegram_service.send_message(update.chat_id, f"❌ Erreur: {str(e)}")

    return None


async def handle_nas_login_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /naslogin command - connect to Synology NAS."""
    from app.services.synology_service import SynologyService

    try:
        service = SynologyService.get_instance()
        service.list_shares()
        await context.telegram_service.send_message(
            update.chat_id,
            f"✓ Connecté au NAS Synology"
        )
    except Exception as e:
        await context.telegram_service.send_message(update.chat_id, f"❌ Erreur de connexion: {str(e)}")

    return None


async def handle_model_command(update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
    """Handle /model command - list or switch models via inline buttons."""
    from app.services.agent_tools.tools.model import ModelSwitchTool

    tool = ModelSwitchTool()

    if not update.text or update.text == "list":
        available = await tool._fetch_available_models()
        provider = tool._get_provider_name()

        keyboard = []
        for m in available:
            model_id = m['id']
            callback_data = f"model_switch:{provider}||{model_id}"
            keyboard.append([{"text": f"✅ {m['name']}", "callback_data": callback_data}])

        reply_markup = {"inline_keyboard": keyboard}
        await context.telegram_service.send_message(
            update.chat_id,
            f"## 🤖 Select a model ({provider}):\n\nTap to switch instantly:",
            reply_markup=reply_markup
        )
        return None

    if update.text.startswith("switch "):
        model_id = update.text[7:].strip()
        available = await tool._fetch_available_models()
        available_ids = [m["id"] for m in available]

        if model_id not in available_ids:
            await context.telegram_service.send_message(
                update.chat_id,
                f"❌ Model `{model_id}` not available.\n\nUse /model list to see available models."
            )
            return None

        is_linked, user = await _require_linked_account(update.chat_id, context)
        if not is_linked:
            return None

        from app.models.user_model_prefs import UserModelPrefs

        provider = tool._get_provider_name()
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
        await context.telegram_service.send_message(
            update.chat_id,
            f"✓ Model switched to `{model_id}` ({provider})\nThis will be used for your next messages."
        )
        return None

    await context.telegram_service.send_message(
        update.chat_id,
        "Usage:\n/model list - Show available models\n/model switch <model_id> - Switch model\n\nExample: /model switch qwen3.5:32b"
    )
    return None


async def _handle_link_token(chat_id: str, token: str, context: HandlerContext) -> Optional[str]:
    """Handle linking via token from /start command."""
    success = context.user_service.link_telegram_chat_id(context.db, token, chat_id)

    if success:
        await context.telegram_service.send_notification(
            chat_id,
            "Account Linked",
            "Your Telegram account is now linked to Tower.",
            "success"
        )
    else:
        await context.telegram_service.send_message(
            chat_id,
            "❌ Link failed. Please use a valid link token from Tower."
        )

    return None


async def _require_linked_account(chat_id: str, context: HandlerContext, action: str = "This action") -> tuple[bool, Optional]:
    """Check if user is linked, send message if not. Returns (is_linked, user)."""
    user = context.user_service.get_by_telegram_chat_id(context.db, chat_id)

    if not user:
        await context.telegram_service.send_message(
            chat_id,
            f"❌ {action} requires linking your account first.\n\nUse /link <email> to link your Tower account."
        )
        return False, None

    return True, user