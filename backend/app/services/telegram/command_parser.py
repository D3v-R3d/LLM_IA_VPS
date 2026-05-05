"""
Telegram Command Parser

Parses and handles Telegram bot commands.
"""

from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of command parsing."""
    command: str
    args: Optional[str]
    handled: bool
    response: Optional[str] = None


class CommandParserService:
    """
    Service for parsing and handling Telegram commands.

    Maps commands to handler functions.
    """

    def __init__(self):
        """Initialize with command handlers."""
        self._handlers: Dict[str, Callable[[Optional[str]], Awaitable[CommandResult]]] = {}

    def register(
        self,
        command: str,
        handler: Callable[[Optional[str]], Awaitable[CommandResult]]
    ) -> None:
        """
        Register a command handler.

        Args:
            command: Command name (without /)
            handler: Async function to handle command
        """
        self._handlers[command] = handler

    def parse(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse command from message text.

        Args:
            text: Message text

        Returns:
            Tuple of (command, arguments)
        """
        if not text or not text.startswith("/"):
            return None, None

        parts = text.split(" ", 1)
        command = parts[0][1:].lower()
        args = parts[1] if len(parts) > 1 else None

        if "@" in command:
            command = command.split("@")[0]

        return command, args

    async def handle(
        self,
        text: str
    ) -> Optional[CommandResult]:
        """
        Handle command and return result.

        Args:
            text: Message text

        Returns:
            CommandResult with response, or None if not a command
        """
        command, args = self.parse(text)

        if not command:
            return None

        if command in self._handlers:
            return await self._handlers[command](args)

        return CommandResult(
            command=command,
            args=args,
            handled=False,
            response=None
        )


class TelegramCommands:
    """Telegram bot commands."""

    START = "start"
    HELP = "help"
    STATUS = "status"
    REGISTER = "register"
    LINK = "link"
    UNLINK = "unlink"
    SETPREF = "setpref"
    PREFS = "prefs"

    ALL = [START, HELP, STATUS, REGISTER, LINK, UNLINK, SETPREF, PREFS]