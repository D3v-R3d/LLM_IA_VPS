"""
Telegram API Router - Transport Layer Only

This module is the entry point for Telegram updates.
It ONLY:
- Receives webhook
- Parses updates
- Dispatches to MessagePipeline
- Returns immediately

It must NOT:
- Orchestrate the agent
- Manage memory
- Manage sessions
- Compress conversations
- Handle tool logic
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, Request, Depends, HTTPException, status
from fastapi import Request as FRequest

from app.services.telegram_service import get_cached_telegram_service
from app.orchestration.message_pipeline import get_message_pipeline
from app.core.lock_manager import get_lock_manager
from app.core.rate_limiter import get_rate_limiter
from app.core.auth import get_current_user
from app.core.config import settings
from app.models.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

telegram_service = get_cached_telegram_service()


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """
    Receive updates from Telegram.

    Returns immediately after dispatching to background processing.
    Never blocks on:
    - LLM
    - Tools
    - Compression
    - Database work
    """
    body = await request.json()
    logger.info(f"Telegram webhook received: update_id={body.get('update_id', 'N/A')}")

    if not _verify_webhook(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token"
        )

    asyncio.create_task(
        _process_update_background(body)
    )

    return {"ok": True}


def _verify_webhook(request: Request) -> bool:
    """Verify the webhook secret token."""
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    return telegram_service.verify_webhook(secret)


async def _process_update_background(body: dict) -> None:
    """Process update in background to not block the webhook response."""
    try:
        pipeline = get_message_pipeline()
        await pipeline.process(body)
    except Exception as e:
        logger.exception(f"Background processing error: {e}")


@router.get("/webhook")
async def verify_webhook(request: Request) -> dict:
    """Webhook verification endpoint (GET for Telegram to verify)."""
    return {"status": "ok"}


@router.get("/health")
async def telegram_health() -> dict:
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
async def set_telegram_commands() -> dict:
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


@router.get("/webhook-info")
async def get_webhook_info() -> dict:
    """Get current webhook info."""
    info = await telegram_service.get_webhook_info()
    if not info:
        raise HTTPException(status_code=500, detail="Failed to get webhook info")

    return info


@router.delete("/webhook")
async def remove_webhook() -> dict:
    """Remove Telegram webhook."""
    success = await telegram_service.delete_webhook()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete webhook")

    return {"status": "ok"}


@router.post("/setup-webhook")
async def setup_webhook(url: str) -> dict:
    """
    Set up Telegram webhook.
    Requires authentication via header.
    """
    secret_token = settings.TELEGRAM_SECRET_TOKEN
    success = await telegram_service.set_webhook(url, secret_token)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to set webhook")

    return {"status": "ok", "webhook_url": url}


@router.post("/notify/{user_id}")
async def send_notification_to_user(
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Send a notification to a user via Telegram.
    Requires authentication.
    """
    from app.services.user_service import UserService
    user_service = UserService()

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
) -> dict:
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


@router.get("/generate-link-token/{user_id}")
async def generate_link_token(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Generate a link token for a user to connect their Telegram.
    Requires authentication. User can only generate their own token.
    """
    from app.services.user_service import UserService
    from app.core.auth import AuthService

    user_service = UserService()

    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot generate tokens for other users"
        )

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    link_token = AuthService.generate_secure_token(32)

    user_service.update_telegram_link_token(db, user_id, link_token)

    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'YOUR_BOT_USERNAME')
    link = f"https://t.me/{bot_username}?start=link_{link_token}"

    return {
        "status": "ok",
        "link_token": link_token,
        "link": link
    }
