"""
Telegram Handlers

Handlers for different types of Telegram updates.
Each handler only knows how to handle its specific update type.
"""

from app.services.telegram.handlers.base import BaseHandler, TelegramUpdate, HandlerContext
from app.services.telegram.handlers.router import HandlerRouter, HandlerRegistry, get_handler_registry
from app.services.telegram.handlers.command_handler import CommandHandler
from app.services.telegram.handlers.text_handler import TextHandler, CallbackQueryHandler

__all__ = [
    "BaseHandler",
    "TelegramUpdate",
    "HandlerContext",
    "HandlerRouter",
    "HandlerRegistry",
    "get_handler_registry",
    "CommandHandler",
    "TextHandler",
    "CallbackQueryHandler",
]
