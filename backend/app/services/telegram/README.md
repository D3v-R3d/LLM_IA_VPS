# Telegram Bot Services

Webhook handling, message sending, and command parsing for Telegram bot integration.

## Architecture

```
Telegram Bot
├── WebhookHandlerService  → Webhook verification and update parsing
├── MessageSenderService  → Send messages/photos/actions to users
└── CommandParserService  → Parse and handle bot commands
```

## Services

### WebhookHandlerService (`webhook.py`)

Handles incoming Telegram webhook updates.

**Key Methods:**
- `verify_webhook(secret_token)` - Verify X-Telegram-Bot-Api-Secret-Token header via HMAC
- `parse_update(update_data)` - Parse raw update dict into TelegramUpdate
- `extract_message_text(update)` - Extract text from message
- `extract_chat_id(update)` - Extract chat ID
- `extract_command(text)` - Extract command and args from text (e.g., `/start arg` → `("start", "arg")`)

### MessageSenderService (`message_sender.py`)

Sends messages via Telegram Bot API using httpx.

**Key Methods:**
- `send_message(chat_id, text, parse_mode="Markdown", ...)` - Send text message
- `send_notification(chat_id, title, message, notification_type)` - Send formatted notification with emoji
- `send_photo(chat_id, photo_url, caption)` - Send photo
- `send_chat_action(chat_id, action)` - Send typing/upload indicator
- `get_me()` - Get bot info
- `health_check()` - Check Telegram API connectivity
- `set_my_commands(commands)` - Set bot command menu

### CommandParserService (`command_parser.py`)

Maps Telegram commands to handler functions.

**Key Methods:**
- `register(command, handler)` - Register handler for command
- `parse(text)` - Parse command and args from message text
- `handle(text)` - Handle command and return CommandResult

**CommandResult Dataclass:**
```python
@dataclass
class CommandResult:
    command: str
    args: Optional[str]
    handled: bool
    response: Optional[str] = None
```

## TelegramCommands

Predefined command constants:

| Constant | Command |
|----------|---------|
| `TelegramCommands.START` | `/start` |
| `TelegramCommands.HELP` | `/help` |
| `TelegramCommands.STATUS` | `/status` |
| `TelegramCommands.REGISTER` | `/register` |
| `TelegramCommands.LINK` | `/link` |
| `TelegramCommands.UNLINK` | `/unlink` |
| `TelegramCommands.SETPREF` | `/setpref` |
| `TelegramCommands.PREFS` | `/prefs` |

## Usage

```python
from app.services.telegram import (
    WebhookHandlerService,
    MessageSenderService,
    CommandParserService,
    TelegramCommands
)

# Webhook verification
handler = WebhookHandlerService()
if handler.verify_webhook(request.headers.get("X-Telegram-Bot-Api-Secret-Token")):
    update = handler.parse_update(update_data)
    chat_id = handler.extract_chat_id(update)

# Send message
sender = MessageSenderService()
await sender.send_message(chat_id, "Hello from TowerBot!")

# Command handling
parser = CommandParserService()
parser.register(TelegramCommands.STATUS, status_handler)
result = await parser.handle("/status")
```

## Key Files

| File | Description |
|------|-------------|
| `webhook.py` | Webhook verification and update parsing |
| `message_sender.py` | Send messages, photos, notifications |
| `command_parser.py` | Command routing to handlers |
| `__init__.py` | Module exports |