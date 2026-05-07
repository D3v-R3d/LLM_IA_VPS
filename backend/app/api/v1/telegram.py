from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from typing import Optional
from uuid import UUID
import logging
import asyncio
import os

from app.services.telegram_service import TelegramService
from app.services.user_service import UserService
from app.models.database import get_db
from app.core.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/telegram", tags=["telegram"])

telegram_service = TelegramService()
user_service = UserService()

logger = logging.getLogger(__name__)

_conversation_locks: dict[str, asyncio.Lock] = {}
_lock_cleanup_interval = 300
_lock_cleanup_task = None

_prompt_cache: dict[str, str] = {}
_prompt_cache_loaded = False


class _LockWithTimestamp(asyncio.Lock):
    """Lock with timestamp tracking for cleanup."""
    def __init__(self):
        super().__init__()
        self._last_used = asyncio.get_event_loop().time()


async def _get_conversation_lock(chat_id: str) -> asyncio.Lock:
    """Get or create a lock for a conversation."""
    if chat_id not in _conversation_locks:
        _conversation_locks[chat_id] = _LockWithTimestamp()
    else:
        lock = _conversation_locks[chat_id]
        if hasattr(lock, '_last_used'):
            lock._last_used = asyncio.get_event_loop().time()
    return _conversation_locks[chat_id]


async def _cleanup_old_locks():
    """Remove locks that are no longer held (older than cleanup interval)."""
    while True:
        try:
            await asyncio.sleep(_lock_cleanup_interval)
            now = asyncio.get_event_loop().time()
            to_remove = []
            for chat_id, lock in _conversation_locks.items():
                if hasattr(lock, '_last_used') and now - lock._last_used > _lock_cleanup_interval:
                    if not lock.locked():
                        to_remove.append(chat_id)
            for chat_id in to_remove:
                del _conversation_locks[chat_id]
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old conversation locks")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Lock cleanup error: {e}")


def start_lock_cleanup():
    """Start the lock cleanup background task."""
    global _lock_cleanup_task
    if _lock_cleanup_task is None or _lock_cleanup_task.done():
        _lock_cleanup_task = asyncio.create_task(_cleanup_old_locks())


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: Session = Depends(get_db)
):
    """
    Receive updates from Telegram.
    """
    body = await request.json()
    logger.info(f"Telegram webhook received: {body.keys()}")

    if not telegram_service.verify_webhook(x_telegram_bot_api_secret_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token"
        )

    callback_query = body.get("callback_query")
    message = body.get("message")

    if callback_query:
        logger.info(f"Callback query detected: {callback_query.get('data')}")
        return await handle_callback_query(callback_query, db)

    if not message:
        return {"status": "ok"}

    chat = message.get("chat")

    chat_id = str(chat["id"])
    text = message["text"]
    message_id = message["message_id"]

    lock = await _get_conversation_lock(chat_id)
    if lock.locked():
        logger.info(f"Chat {chat_id} is already processing, acknowledging duplicate")
        await telegram_service.send_message(chat_id, "⏳ Je traite votre message précédent...")
        return {"status": "ok", "queued": True}

    async with lock:
        command, args = telegram_service.parse_command(text)

        max_message_length = 4000
        if len(text) > max_message_length:
            await telegram_service.send_message(
                chat_id,
                f"❌ Message trop long ({len(text)}/{max_message_length} caractères). Merci de réduire la taille."
            )
            return {"status": "ok"}

        if command == "start":
            await handle_start_command(chat_id, args, db)
        elif command == "help":
            await telegram_service.send_help_message(chat_id)
        elif command == "status":
            await handle_status_command(chat_id, db)
        elif command == "link":
            await handle_link_command(chat_id, args, db)
        elif command == "unlink":
            await handle_unlink_command(chat_id, db)
        elif command == "register":
            await handle_register_command(chat_id, args, db)
        elif command == "setpref":
            await handle_setpref_command(chat_id, args, db)
        elif command == "prefs":
            await handle_prefs_command(chat_id, db)
        elif command == "sessions":
            await handle_sessions_command(chat_id, db)
        elif command == "new":
            await handle_new_command(chat_id, args, db)
        elif command == "reset":
            await handle_reset_command(chat_id, db)
        elif command == "compress":
            await handle_compress_command(chat_id, db)
        elif command == "nas":
            await handle_nas_command(chat_id, args, db)
        elif command == "ls":
            await handle_ls_command(chat_id, args, db)
        elif command == "naslogin":
            await handle_nas_login_command(chat_id, db)
        else:
            await handle_text_message(chat_id, text, db)

    return {"status": "ok"}


async def handle_register_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /register command - redirect to web app."""
    return await telegram_service.send_message(
        chat_id,
        "❌ Registration is not available via Telegram.\n\n"
        "Please register via the web app at:\n"
        "https://www.srv1632761.hstgr.cloud\n\n"
        "After registering, use /link <email> to link your account."
    )


async def handle_start_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /start command."""
    if args and args.startswith("link_"):
        token = args[5:]
        return await handle_link_token(chat_id, token, db)

    return await telegram_service.send_welcome_message(chat_id)


async def handle_link_token(chat_id: str, token: str, db: Session) -> bool:
    """Handle linking via token from /start command."""
    success = user_service.link_telegram_chat_id(db, token, chat_id)
    if success:
        return await telegram_service.send_notification(
            chat_id,
            "Account Linked",
            "Your Telegram account is now linked to Tower.",
            "success"
        )
    else:
        return await telegram_service.send_message(
            chat_id,
            "❌ Link failed. Please use a valid link token from Tower."
        )


async def handle_status_command(chat_id: str, db: Session) -> bool:
    """Handle /status command."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
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

    return await telegram_service.send_message(chat_id, text)


async def handle_link_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /link <email> command."""
    if not args:
        return await telegram_service.send_message(
            chat_id,
            "Usage: /link <email>\n\nExample: /link user@example.com"
        )

    success = user_service.link_telegram_chat_id_by_email(db, args, chat_id)
    if success:
        return await telegram_service.send_notification(
            chat_id,
            "Account Linked",
            f"Telegram linked to {args}",
            "success"
        )
    else:
        return await telegram_service.send_message(
            chat_id,
            "❌ Link failed. User not found or already linked."
        )


async def handle_unlink_command(chat_id: str, db: Session) -> bool:
    """Handle /unlink command."""
    success = user_service.unlink_telegram_chat_id(db, chat_id)
    if success:
        return await telegram_service.send_notification(
            chat_id,
            "Account Unlinked",
            "Your Telegram account has been unlinked from Tower.",
            "info"
        )
    else:
        return await telegram_service.send_message(
            chat_id,
            "❌ Unlink failed. No account was linked."
        )


async def handle_setpref_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /setpref key=value command."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    if not args or "=" not in args:
        return await telegram_service.send_message(
            chat_id,
            "Usage: /setpref key=value\n\nExamples:\n/setpref name=John\n/setpref language=fr\n/setpref style=concise\n/setpref timezone=Europe/Paris"
        )

    try:
        key, value = args.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if not key or not value:
            return await telegram_service.send_message(
                chat_id,
                "❌ Invalid format. Use: /setpref key=value"
            )

        success = user_service.set_preference(db, user.id, key, value)
        if success:
            return await telegram_service.send_notification(
                chat_id,
                "Preference Set",
                f"✓ {key} = {value}",
                "success"
            )
        else:
            return await telegram_service.send_message(
                chat_id,
                "❌ Failed to set preference"
            )
    except Exception as e:
        logger.error(f"Error setting preference: {e}")
        return await telegram_service.send_message(
            chat_id,
            "Failed to set preference. Please try again."
        )


async def handle_prefs_command(chat_id: str, db: Session) -> bool:
    """Handle /prefs command - show user preferences."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    prefs = user_service.get_preferences(db, user.id)

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

    return await telegram_service.send_message(chat_id, text)


async def handle_sessions_command(chat_id: str, db: Session) -> bool:
    """Handle /sessions command - list all sessions."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    from app.services.conversation_service import ConversationService
    conversation_service = ConversationService()

    sessions = conversation_service.get_all_telegram_sessions(db, user.id)
    prefs = user_service.get_preferences(db, user.id)
    current = prefs.get("current_session", "default")

    if not sessions:
        text = "*Your Sessions*\n\nNo sessions yet. Start chatting to create one!"
    else:
        lines = ["*Your Sessions*\n"]
        for s in sessions:
            marker = "✓" if s.telegram_chat_id == current else " "
            lines.append(f"{marker} {s.title} ({s.telegram_chat_id[:8]})")
        text = "\n".join(lines)

    return await telegram_service.send_message(chat_id, text)


async def handle_new_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /new command - start a new session."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    import uuid
    session_id = str(uuid.uuid4())
    title = args.strip() if args and args.strip() else f"Session {session_id[:8]}"

    from app.services.conversation_service import ConversationService
    conversation_service = ConversationService()

    conversation = conversation_service.create_telegram_session(db, user.id, session_id, title)
    user_service.set_preference(db, user.id, "current_session", session_id)

    return await telegram_service.send_notification(
        chat_id,
        "New Session Started",
        f"✓ {title}\n\nAll messages will be in this session.",
        "success"
    )


async def handle_reset_command(chat_id: str, db: Session) -> bool:
    """Handle /reset command - clear current session and start fresh."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    prefs = user_service.get_preferences(db, user.id)
    current_session = prefs.get("current_session")

    if current_session:
        from app.services.conversation_service import ConversationService
        conversation_service = ConversationService()
        conv = conversation_service.get_telegram_session(db, user.id, current_session)
        if conv:
            from app.services.message_service import MessageService
            message_service = MessageService()
            for msg in conv.messages:
                message_service.delete(db, msg.id)

    user_service.set_preference(db, user.id, "current_session", None)

    return await telegram_service.send_notification(
        chat_id,
        "Session Reset",
        "✓ Context cleared. Starting fresh!",
        "info"
    )


async def handle_compress_command(chat_id: str, db: Session) -> bool:
    """Handle /compress command - summarize and compress conversation history."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        return await telegram_service.send_message(
            chat_id,
            "❌ Please link your account first using /link <email>"
        )

    prefs = user_service.get_preferences(db, user.id)
    current_session = prefs.get("current_session")

    if current_session:
        from app.services.conversation_service import ConversationService
        conversation_service = ConversationService()
        conversation = conversation_service.get_telegram_session(db, user.id, current_session)
    else:
        conversation = conversation_service.get_telegram_conversation(db, user.id)

    if not conversation:
        return await telegram_service.send_message(
            chat_id,
            "❌ No active session found."
        )

    token_count = conversation_service.get_token_count(conversation)

    if token_count < 500:
        return await telegram_service.send_message(
            chat_id,
            f"✅ Session is already compact ({token_count} tokens). No compression needed."
        )

    await telegram_service.send_chat_action(chat_id, "typing")

    summary = conversation_service.compress_conversation(db, conversation.id, keep_last=15)

    new_count = conversation_service.get_token_count(conversation)

    if summary:
        return await telegram_service.send_notification(
            chat_id,
            "Session Compressed",
            f"✓ {token_count} → {new_count} tokens\n\n{summary[:200]}...",
            "success"
        )
    else:
        return await telegram_service.send_message(
            chat_id,
            f"❌ Compression failed or not needed."
        )


async def handle_nas_login_command(chat_id: str, db: Session) -> bool:
    """Handle /naslogin command - connect to Synology NAS."""
    from app.services.synology import SynologyClient, SynologyAuth

    try:
        client = SynologyClient()
        auth = SynologyAuth(client)
        token = auth.login()
        await telegram_service.send_message(chat_id, f"✓ Connecté au NAS Synology\nSID: {token[:20]}...")
        return True
    except Exception as e:
        await telegram_service.send_message(chat_id, f"❌ Erreur de connexion: {str(e)}")
        return True


async def handle_nas_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /nas command - list shares on NAS."""
    from app.services.synology import SynologyClient, SynologyAuth, FileStation

    try:
        client = SynologyClient()
        auth = SynologyAuth(client)
        auth.login()

        fs = FileStation(client)
        shares = fs.list_shares()
        share_list = shares.get("data", {}).get("shares", [])

        if not share_list:
            await telegram_service.send_message(chat_id, "Aucun partage trouvé.")
            return True

        lines = ["📁 *Partages NAS:*\n"]
        for s in share_list:
            lines.append(f"• {s['name']} ({s['path']})")

        await telegram_service.send_message(chat_id, "\n".join(lines))
        return True
    except Exception as e:
        await telegram_service.send_message(chat_id, f"❌ Erreur: {str(e)}")
        return True


async def handle_ls_command(chat_id: str, args: Optional[str], db: Session) -> bool:
    """Handle /ls command - list files in a NAS folder."""
    from app.services.synology import SynologyClient, SynologyAuth, FileStation

    if not args:
        await telegram_service.send_message(chat_id, "Usage: /ls <dossier>\nExemple: /ls /chat")
        return True

    folder_path = args if args.startswith("/") else f"/{args}"

    try:
        client = SynologyClient()
        auth = SynologyAuth(client)
        auth.login()

        fs = FileStation(client)
        result = fs.list_folders(folder_path)
        files = result.get("data", {}).get("files", [])

        if not files:
            await telegram_service.send_message(chat_id, f"Dossier vide: {folder_path}")
            return True

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
            await telegram_service.send_message(
                chat_id,
                "\n".join(text_lines),
                reply_markup=reply_markup
            )
        else:
            await telegram_service.send_message(chat_id, "\n".join(text_lines))

        return True
    except Exception as e:
        await telegram_service.send_message(chat_id, f"❌ Erreur: {str(e)}")
        return True


def _format_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


async def handle_text_message(chat_id: str, text: str, db: Session) -> bool:
    """Handle regular text messages - save to DB, send to Ollama, respond via bot."""
    import sys
    print(f"HANDLE_TEXT_START: chat_id={chat_id}, text={text}", flush=True)
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        await telegram_service.send_message(
            chat_id,
            "Please link your account first using /link <email>"
        )
        return False

    from app.services.conversation_service import ConversationService
    from app.services.message_service import MessageService
    from app.schemas.message import MessageCreate

    conversation_service = ConversationService()
    message_service = MessageService()

    prefs = user_service.get_preferences(db, user.id)
    current_session = prefs.get("current_session")

    if current_session:
        conversation = conversation_service.get_telegram_session(db, user.id, current_session)
        if not conversation:
            conversation = conversation_service.create_telegram_session(db, user.id, current_session)
    else:
        conversation = conversation_service.get_by_telegram_chat_id(db, chat_id)

    if not conversation:
        conversation = conversation_service.create_telegram_session(db, user.id, chat_id)

    from app.services.context_service import ContextService, CONTEXT_CONFIG

    context_service = ContextService()

    if context_service.should_compress(conversation):
        await telegram_service.send_chat_action(chat_id, "typing")
        await context_service.compress_conversation_async(db, conversation)

    await telegram_service.send_chat_action(chat_id, "typing")

    message_data = MessageCreate(
        conversation_id=conversation.id,
        role="user",
        content=text
    )
    user_msg = message_service.create(
        db=db,
        user_id=user.id,
        message_data=message_data
    )

    messages_history = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages[-CONTEXT_CONFIG["max_messages"]:]
    ]

    from app.services.tools_service import ToolsService
    from app.services.agent_tools import get_tool_definitions

    tools_service = ToolsService()
    web_tools = tools_service.get_tools()
    agent_tools = get_tool_definitions()
    tools = web_tools + agent_tools

    global _prompt_cache, _prompt_cache_loaded
    if not _prompt_cache_loaded:
        prompt_folder = "/home/projects/tower_project/prompt"
        try:
            for filename in os.listdir(prompt_folder):
                if filename.endswith(".md") and filename != "context_summary.md":
                    filepath = os.path.join(prompt_folder, filename)
                    try:
                        with open(filepath, "r") as f:
                            content = f.read()
                        sections = content.split("---")
                        _prompt_cache[filename] = sections[0].strip() if sections else content.strip()
                    except Exception:
                        pass
            _prompt_cache_loaded = True
        except Exception:
            _prompt_cache_loaded = True

    prompt_files_content = dict(_prompt_cache)

    context_summary = ""
    try:
        summary_path = "/home/projects/tower_project/prompt/context_summary.md"
        with open(summary_path, "r") as f:
            parts = f.read().split("<!-- Summary will be injected here -->")
            if len(parts) > 1:
                context_summary = parts[1].strip()
    except Exception:
        pass

    pref_text = ""
    if prefs:
        pref_lines = [f"• {k}: {v}" for k, v in prefs.items() if k != "current_session"]
        if pref_lines:
            pref_text = "\nUser preferences:\n" + "\n".join(pref_lines)

    files_section = ""
    for filename, content in prompt_files_content.items():
        if content:
            files_section += f"\n\n=== {filename} ===\n{content[:2000]}"
    files_section = files_section[:8000]

    context_section = f"\n\n### Previous Conversation Summary:\n{context_summary}\n" if context_summary else ""

    system_message = {
        "role": "system",
        "content": f"""You are a helpful assistant.{context_section}{files_section}

WEB TOOLS: search_web, fetch_url, call_api, search_and_fetch
NAS TOOLS: nas_list_share, nas_list_folder, nas_search
SYSTEM TOOLS: read_file, write_file, edit_file, glob, grep, ls, bash, docker, git, pkill
DB TOOLS: postgres_query, postgres_list_tables, postgres_describe_table
TELEGRAM TOOLS: telegram_send_message, telegram_send_notification, telegram_get_user_info, telegram_bot_health

User preferences:{pref_text}
CRITICAL RULES:
- NEVER invent, embellish, or hallucinate any data, facts, names, numbers, or information not returned by tools.
- When using tools, return ONLY actual data. Do NOT add rows, columns, values, statistics, or details that were not in the tool result.
- If data is missing or you are unsure, say so clearly instead of making up information.
- Use tools when needed. Do NOT make up tool names."""
    }

    messages_with_system = [system_message] + messages_history

    try:
        from app.services.agent_service import AgentService

        agent = AgentService(telegram_service=telegram_service)
        assistant_reply = await agent.run_agent_loop(
            user_message=text,
            chat_id=chat_id,
            messages_history=messages_history,
            system_prompt=system_message["content"],
            tools=tools,
            user_id=str(user.id)
        )
        await agent.close()
    except Exception as e:
        logger.exception(f"Agent error: {e}")
        assistant_reply = "I'm thinking... Please try again in a moment."

    if not assistant_reply or not assistant_reply.strip():
        assistant_reply = "Here's what I found."

    message_data = MessageCreate(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_reply
    )
    message_service.create(
        db=db,
        user_id=user.id,
        message_data=message_data
    )

    conversation_service.update_timestamp(db, conversation.id)

    print(f"HANDLE_TEXT_END: chat_id={chat_id}, sending reply", flush=True)
    try:
        result = await telegram_service.send_message(chat_id, assistant_reply)
        print(f"SEND_RESULT: {result}", flush=True)
    except Exception as e:
        print(f"SEND_ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    print(f"HANDLE_TEXT_SUCCESS: chat_id={chat_id}", flush=True)

    return True


async def handle_callback_query(callback_query: dict, db: Session) -> dict:
    """Handle inline button clicks."""
    query_id = callback_query["id"]
    chat_id = str(callback_query["message"]["chat"]["id"])
    data = callback_query.get("data", "")

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Callback query received: data={data}, chat_id={chat_id}")

    if data.startswith("/ls"):
        await handle_ls_command(chat_id, data[3:].strip(), db)
        return {"status": "ok"}

    if data.startswith("conv_"):
        conversation_id = data[5:]
        await telegram_service.answer_callback_query(
            query_id,
            text="Opening conversation...",
            show_alert=False
        )
        return {"status": "ok", "conversation_id": conversation_id}

    await telegram_service.answer_callback_query(
        query_id,
        text="Unknown action",
        show_alert=True
    )
    return {"status": "ok"}


@router.post("/notify/{user_id}")
async def send_notification_to_user(
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a notification to a user via Telegram.
    Requires authentication.
    """
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send notifications to other users"
        )

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="User has no linked Telegram account"
        )

    sent = await telegram_service.send_notification(
        user.telegram_chat_id,
        title,
        message,
        notification_type
    )

    return {"status": "ok", "sent": sent}


@router.post("/notify/conversation/{conversation_id}")
async def notify_conversation(
    conversation_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a notification to all users in a conversation.
    Requires authentication.
    """
    from app.services.conversation_service import ConversationService

    conversation_service = ConversationService()
    conversation = conversation_service.get_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if str(conversation.user_id) != str(current_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    count = 0
    for participant in conversation.participants:
        if participant.telegram_chat_id:
            sent = await telegram_service.send_notification(
                participant.telegram_chat_id,
                title,
                message,
                notification_type
            )
            if sent:
                count += 1

    return {"status": "ok", "notified": count}


@router.post("/setup-webhook")
async def setup_webhook(
    url: str,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set up Telegram webhook.
    Requires authentication.
    """
    from app.core.config import settings

    secret_token = settings.TELEGRAM_SECRET_TOKEN
    success = await telegram_service.set_webhook(url, secret_token)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to set webhook"
        )

    return {"status": "ok", "webhook_url": url}


@router.delete("/webhook")
async def remove_webhook(current_user_id: UUID = Depends(get_current_user)):
    """
    Remove Telegram webhook.
    Requires authentication.
    """
    success = await telegram_service.delete_webhook()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete webhook")

    return {"status": "ok"}


@router.get("/webhook-info")
async def get_webhook_info(current_user_id: UUID = Depends(get_current_user)):
    """
    Get current webhook info.
    Requires authentication.
    """
    info = await telegram_service.get_webhook_info()
    if not info:
        raise HTTPException(status_code=500, detail="Failed to get webhook info")

    return info


@router.get("/health")
async def telegram_health():
    """
    Check Telegram bot health.
    Public endpoint.
    """
    healthy = await telegram_service.health_check()
    bot_info = await telegram_service.get_me()

    return {
        "status": "ok",
        "healthy": healthy,
        "bot_info": bot_info
    }


@router.post("/set-commands")
async def set_telegram_commands():
    """
    Set bot command menu.
    Updates the bot's command list in Telegram.
    """
    commands = [
        {"command": "nas", "description": "List NAS shares"},
        {"command": "ls", "description": "List NAS folder contents"},
        {"command": "status", "description": "Check account status"},
        {"command": "link", "description": "Link your account"},
        {"command": "unlink", "description": "Unlink your account"},
        {"command": "new", "description": "Start new session"},
        {"command": "reset", "description": "Clear conversation"},
        {"command": "compress", "description": "Summarize conversation"},
        {"command": "sessions", "description": "List your sessions"},
        {"command": "prefs", "description": "Show preferences"},
        {"command": "help", "description": "Show help"},
    ]
    
    success = await telegram_service.set_my_commands(commands)
    return {"status": "ok", "commands_set": success}


@router.get("/generate-link-token/{user_id}")
async def generate_link_token(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a link token for a user to connect their Telegram.
    Requires authentication. User can only generate their own token.
    """
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot generate tokens for other users"
        )

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.auth import AuthService
    link_token = AuthService.generate_secure_token(32)

    user_service.update_telegram_link_token(db, user_id, link_token)

    from app.core.config import settings
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'YOUR_BOT_USERNAME')
    link = f"https://t.me/{bot_username}?start=link_{link_token}"

    return {
        "status": "ok",
        "link_token": link_token,
        "link": link
    }