# Data Models

This directory contains SQLAlchemy ORM models for database entities.

## Structure

```
models/
├── database.py         # SQLAlchemy engine, session, base class
├── mixins.py           # Reusable model mixins (TimestampMixin)
├── user.py             # User entity
├── conversation.py      # Conversation entity
├── message.py          # Message entity
├── document.py         # Document entity
└── __init__.py         # Package exports
```

## Database Connection (`database.py`)

- `engine`: SQLAlchemy engine connected to PostgreSQL
- `SessionLocal`: Session factory for database connections
- `Base`: Declarative base for all models
- `get_db()`: FastAPI dependency for session injection

## Mixins (`mixins.py`)

Reusable model components:

- `TimestampMixin`: Adds `created_at` timestamp field

## Entity Models

### User (`user.py`)

Represents application users.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| email | String | Unique email address |
| password_hash | String | Bcrypt hashed password |
| name | String | Display name |
| created_at | DateTime | Account creation timestamp |
| last_login | DateTime | Last login (nullable) |
| telegram_chat_id | String | Telegram chat ID (nullable) |
| telegram_link_token | String | Token for linking Telegram |
| preferences | JSONB | User preferences |

**Relationships:** User → Conversation, Message, Document (one-to-many)

### Conversation (`conversation.py`)

Represents a chat session.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| title | String | Conversation title (optional) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last modification timestamp |
| telegram_chat_id | String | Telegram chat ID (optional) |

**Relationships:** Conversation → User (many-to-one), Conversation → Message (one-to-many)

### Message (`message.py`)

Represents a single message in a conversation.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| conversation_id | UUID | Foreign key to Conversation |
| role | Enum | Sender role (user/assistant) |
| content | Text | Message content |
| created_at | DateTime | Creation timestamp |

**Relationships:** Message → User, Conversation (many-to-one)

### Document (`document.py`)

Represents an uploaded document for RAG processing.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| name | String | Document name |
| content_raw | Text | Raw content |
| type | String | Document type (pdf, txt, md) |
| is_embedded | Boolean | Whether document is embedded |
| created_at | DateTime | Upload timestamp |

**Relationships:** Document → User (many-to-one)

## Usage

```python
from app.models import User, Conversation, Message, Document
from app.models.database import get_db

# FastAPI dependency
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

## Entity Relationship Diagram

```
┌─────────┐       ┌────────────────┐       ┌──────────┐
│  User   │──┬────│  Conversation  │──┐────│  Message │
└─────────┘  │    └────────────────┘  │    └──────────┘
             │                        │
             │    ┌────────────────┐  │
             └───▶│   Document     │  │
                  └────────────────┘  │
```

## Security

- UUID primary keys prevent enumeration
- Bcrypt password hashing
- CASCADE deletes for referential integrity
- Unique email constraint