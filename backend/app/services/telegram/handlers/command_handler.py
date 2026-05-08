"""
Command Handler for Telegram /commands

Handles all /command style messages by dispatching to specific command handlers.
"""

import logging
from typing import Optional

from app.services.telegram.handlers.base import BaseHandler, TelegramUpdate, HandlerContext

logger = logging.getLogger(__name__)


class CommandHandler(BaseHandler):
    """
    Handles Telegram /command messages.

    Dispatches to registered command functions based on command name.
    """

    COMMAND_HANDLERS = {}

    @classmethod
    def register_command(cls, command: str, handler):
        """Register a command handler function."""
        cls.COMMAND_HANDLERS[command] = handler

    async def can_handle(self, update: TelegramUpdate) -> bool:
        """Check if this is a command (starts with /)."""
        return update.command is not None

    async def handle(self, update: TelegramUpdate, context: HandlerContext) -> Optional[str]:
        """Handle the command by dispatching to registered handler."""
        command = update.command

        if command not in self.COMMAND_HANDLERS:
            logger.warning(f"No handler for command: {command}")
            return f"Unknown command: {command}"

        handler = self.COMMAND_HANDLERS[command]

        try:
            if callable(handler):
                result = await handler(update, context)
                return result
        except Exception as e:
            logger.exception(f"Command handler error for {command}: {e}")
            return f"Error processing {command}"

        return None


def _register_all_commands():
    """Register all known commands."""
    from app.services.telegram.handlers.commands import (
        handle_start_command,
        handle_help_command,
        handle_status_command,
        handle_link_command,
        handle_unlink_command,
        handle_register_command,
        handle_setpref_command,
        handle_prefs_command,
        handle_sessions_command,
        handle_new_command,
        handle_reset_command,
        handle_compress_command,
        handle_nas_command,
        handle_ls_command,
        handle_nas_login_command,
        handle_model_command,
    )

    CommandHandler.register_command("/start", handle_start_command)
    CommandHandler.register_command("/help", handle_help_command)
    CommandHandler.register_command("/status", handle_status_command)
    CommandHandler.register_command("/link", handle_link_command)
    CommandHandler.register_command("/unlink", handle_unlink_command)
    CommandHandler.register_command("/register", handle_register_command)
    CommandHandler.register_command("/setpref", handle_setpref_command)
    CommandHandler.register_command("/prefs", handle_prefs_command)
    CommandHandler.register_command("/sessions", handle_sessions_command)
    CommandHandler.register_command("/new", handle_new_command)
    CommandHandler.register_command("/reset", handle_reset_command)
    CommandHandler.register_command("/compress", handle_compress_command)
    CommandHandler.register_command("/nas", handle_nas_command)
    CommandHandler.register_command("/ls", handle_ls_command)
    CommandHandler.register_command("/naslogin", handle_nas_login_command)
    CommandHandler.register_command("/model", handle_model_command)
    CommandHandler.register_command("/models", handle_model_command)


_register_all_commands()