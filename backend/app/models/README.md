# Data Models

This directory contains database models and session management for the Tower Project application.

## Structure

```
models/
├── database.py         # SQLAlchemy engine, session, and base class
├── user.py             # User entity model
├── conversation.py     # Conversation entity model
├── message.py          # Message entity model
├── document.py         # Document entity model
└── __init__.py         # Package exports
```

## Database Connection

`database.py` manages:

- SQLAlchemy engine creation
- Session factory for database connections
- Base class for model definitions
- Dependency injection via `get_db()` function

## Entity Models

### User Model (`user.py`)

Represents application users.

**Attributes:**
- `id` (UUID, PK): Unique identifier
- `email` (String, unique): User's email address
- `password_hash` (String): Bcrypt hashed password
- `name` (String): Display name
- `created_at` (DateTime): Account creation timestamp
- `last_login` (DateTime): Last login timestamp (nullable)

**Relationships:**
- User → Conversation (one-to-many)
- User → Message (one-to-many)
- User → Document (one-to-many)

### Conversation Model (`conversation.py`)

Represents a chat session between user and LLM.

**Attributes:**
- `id` (UUID, PK): Unique identifier
- `user_id` (UUID, FK): Owner user reference
- `title` (String): Optional conversation title
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last modification timestamp

**Relationships:**
- Conversation → User (many-to-one)
- Conversation → Message (one-to-many)

### Message Model (`message.py`)

Represents a single message in a conversation.

**Attributes:**
- `id` (UUID, PK): Unique identifier
- `user_id` (UUID, FK): Sender user reference
- `conversation_id` (UUID, FK): Parent conversation reference
- `role` (Enum): Sender role (user | assistant)
- `content` (Text): Message text content
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Message → User (many-to-one)
- Message → Conversation (many-to-one)

**Qdrant Integration:** YES - Content is embedded for semantic search.

### Document Model (`document.py`)

Represents an uploaded file for RAG processing.

**Attributes:**
- `id` (UUID, PK): Unique identifier
- `user_id` (UUID, FK): Owner user reference
- `name` (String): Document name/title
- `content_raw` (Text): Raw content or file path
- `type` (String): Document type (pdf, txt, md, etc.)
- `created_at` (DateTime): Upload timestamp

**Relationships:**
- Document → User (many-to-one)

**Qdrant Integration:** YES - Chunks are OBLIGATORILY embedded for RAG.

## Usage

### Creating Tables

```python
from app.models import Base, engine
Base.metadata.create_all(bind=engine)
```

### Querying Data

```python
from app.models import User, Conversation, Message
from app.models.database import SessionLocal

db = SessionLocal()
try:
    # Get user with conversations
    user = db.query(User).filter(User.email == "user@example.com").first()

    # Access user's conversations
    for conv in user.conversations:
        print(f"Conversation: {conv.title}")

    # Access messages in a conversation
    for msg in conv.messages:
        print(f"{msg.role}: {msg.content}")
finally:
    db.close()
```

### Database Session

```python
from app.models.database import get_db

# FastAPI dependency injection
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

## Qdrant Integration

Models are designed for vector storage in Qdrant:

### Message Embeddings
- **Text embedded:** Message content
- **Payload:** message_id, user_id, conversation_id, role, timestamp

### Conversation Embeddings
- **Text embedded:** Summary or last context messages
- **Payload:** conversation_id, user_id, last_summary, updated_at

### Document Embeddings (Chunks)
- **Text embedded:** Chunk text
- **Payload:** document_id, chunk_id, user_id, text, page, created_at

## Entity Relationship Diagram

```
┌─────────┐       ┌────────────────┐       ┌──────────┐
│  User   │──┬────│  Conversation  │──┬────│  Message │
└─────────┘  │    └────────────────┘  │    └──────────┘
             │                        │
             │    ┌────────────────┐  │
             └───▶│   Document      │  │
                  └────────────────┘  │
                                       │
         (1:N relationships)           │
```

## Security

- UUID primary keys prevent enumeration attacks
- Passwords stored as bcrypt hashes (never plain text)
- CASCADE deletes ensure referential integrity
- Email unique constraint prevents duplicate accounts