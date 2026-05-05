from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from typing import Optional
from uuid import UUID

from app.services.telegram_service import TelegramService
from app.services.user_service import UserService
from app.models.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/telegram", tags=["telegram"])

telegram_service = TelegramService()
user_service = UserService()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: Session = Depends(get_db)
):
    """
    Receive updates from Telegram.

    This endpoint is called by Telegram when:
    - A user sends a message to the bot
    - A user clicks an inline button
    - etc.

    For verification, Telegram sends a GET request first to check the webhook.
    """
    body = await request.json()

    if not telegram_service.verify_webhook(x_telegram_bot_api_secret_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token"
        )

    message = body.get("message")
    if not message:
        return {"status": "ok"}

    chat = message.get("chat")
    callback_query = body.get("callback_query")

    if callback_query:
        return await handle_callback_query(callback_query, db)

    if not chat or not message.get("text"):
        return {"status": "ok"}

    chat_id = str(chat["id"])
    text = message["text"]
    message_id = message["message_id"]

    command, args = telegram_service.parse_command(text)

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
    else:
        await handle_text_message(chat_id, text, db)

    return {"status": "ok"}


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
        return await telegram_service.send_message(
            chat_id,
            f"❌ Error: {str(e)}"
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


async def handle_text_message(chat_id: str, text: str, db: Session) -> bool:
    """Handle regular text messages - save to DB, send to Ollama, respond via bot."""
    user = user_service.get_by_telegram_chat_id(db, chat_id)
    if not user:
        await telegram_service.send_message(
            chat_id,
            "Please link your account first using /link <email>"
        )
        return False

    from app.services.conversation_service import ConversationService
    from app.services.message_service import MessageService
    from app.services.llm_service import LLMService
    from app.core.config import settings
    from app.schemas.message import MessageCreate
    from datetime import datetime, timezone

    conversation_service = ConversationService()
    message_service = MessageService()
    llm_service = LLMService(
        base_url=settings.OLLAMA_CLOUD_HOST,
        api_key=settings.OLLAMA_API_KEY
    )

    prefs = user_service.get_preferences(db, user.id)
    current_session = prefs.get("current_session")

    if current_session:
        conversation = conversation_service.get_telegram_session(db, user.id, current_session)
        if not conversation:
            conversation = conversation_service.create_telegram_session(db, user.id, current_session)
    else:
        conversation = conversation_service.get_telegram_conversation(db, user.id)

    from app.services.context_service import ContextService, CONTEXT_CONFIG
    context_service = ContextService()

    if context_service.should_compress(conversation):
        await telegram_service.send_chat_action(chat_id, "typing")
        context_service.compress_conversation(db, conversation)

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
        for m in conversation.messages[-20:]
    ]

    from app.services.tools_service import ToolsService
    tools_service = ToolsService()
    tools = tools_service.get_tools()

    pref_text = ""
    if prefs:
        pref_lines = [f"• {k}: {v}" for k, v in prefs.items() if k != "current_session"]
        if pref_lines:
            pref_text = "\nUser preferences:\n" + "\n".join(pref_lines)

    system_message = {
        "role": "system",
        "content": f"""You are a helpful assistant with web access.{pref_text}
When answering questions:
1. Use search_and_fetch for current info - do NOT guess
2. For dates, search first
3. If info seems outdated, warn the user
4. Remember user preferences and apply them
5. Always prefer searching over guessing."""
    }

    messages_with_system = [system_message] + messages_history

    try:
        response = await llm_service.chat_with_tools(
            model="minimax-m2.7",
            messages=messages_with_system,
            tools=tools
        )
        assistant_reply = response.get("message", {}).get("content", "Sorry, I couldn't process that.")
    except Exception as e:
        assistant_reply = f"Error: {str(e)}"

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

    await llm_service.close()

    await telegram_service.send_message(chat_id, assistant_reply)

    return True


async def handle_callback_query(callback_query: dict, db: Session) -> dict:
    """Handle inline button clicks."""
    query_id = callback_query["id"]
    chat_id = str(callback_query["message"]["chat"]["id"])
    data = callback_query.get("data", "")

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
    db: Session = Depends(get_db)
):
    """
    Send a notification to a user via Telegram.

    Args:
        user_id: UUID of the user to notify
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)

    Returns:
        {"status": "ok", "sent": bool}
    """
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
    db: Session = Depends(get_db)
):
    """
    Send a notification to all users in a conversation.

    Args:
        conversation_id: UUID of the conversation
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)

    Returns:
        {"status": "ok", "notified": int}
    """
    from app.services.conversation_service import ConversationService

    conversation_service = ConversationService()
    conversation = conversation_service.get_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

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
    db: Session = Depends(get_db)
):
    """
    Set up Telegram webhook.

    Args:
        url: Full HTTPS URL for the webhook

    Returns:
        {"status": "ok", "webhook_url": str}
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
async def remove_webhook():
    """
    Remove Telegram webhook.

    Returns:
        {"status": "ok"}
    """
    success = await telegram_service.delete_webhook()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete webhook")

    return {"status": "ok"}


@router.get("/webhook-info")
async def get_webhook_info():
    """
    Get current webhook info.

    Returns:
        Webhook info dict
    """
    info = await telegram_service.get_webhook_info()
    if not info:
        raise HTTPException(status_code=500, detail="Failed to get webhook info")

    return info


@router.get("/health")
async def telegram_health():
    """
    Check Telegram bot health.

    Returns:
        {"status": "ok", "healthy": bool, "bot_info": dict}
    """
    healthy = await telegram_service.health_check()
    bot_info = await telegram_service.get_me()

    return {
        "status": "ok",
        "healthy": healthy,
        "bot_info": bot_info
    }


@router.get("/generate-link-token/{user_id}")
async def generate_link_token(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate a link token for a user to connect their Telegram.

    Args:
        user_id: UUID of the user

    Returns:
        {"status": "ok", "link_token": str, "link": str}
    """
    from app.core.config import settings

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    import hashlib
    import time

    token_source = f"{user_id}{user.email}{time.time()}"
    link_token = hashlib.sha256(token_source.encode()).hexdigest()[:32]

    user_service.update_telegram_link_token(db, user_id, link_token)

    from app.core.config import settings
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'YOUR_BOT_USERNAME')
    link = f"https://t.me/{bot_username}?start=link_{link_token}"

    return {
        "status": "ok",
        "link_token": link_token,
        "link": link
    }