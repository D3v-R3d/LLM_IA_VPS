# Data Models

This directory contains database models and session management.

## Structure

```
models/
├── database.py       # Database session and engine
└── __init__.py
```

## Database Connection

`database.py` manages:

- SQLAlchemy engine creation
- Session factory for database connections
- Dependency injection via `get_db()` function

### Configuration

The database connection is configured using the `DATABASE_URL` environment variable:

```
postgresql://postgres:password@postgres:5432/tower_db
```

### Usage

```python
from app.models.database import get_db, SessionLocal, Base

# Get a database session
def some_function():
    db = next(get_db())
    try:
        # Use db session
        pass
    finally:
        db.close()
```

### Key Components

- `engine`: SQLAlchemy engine instance
- `SessionLocal`: Session factory for creating database sessions
- `Base`: Declarative base class for model definitions
- `get_db()`: Generator function for dependency injection

## Models

Database models define:
- Table structures using SQLAlchemy ORM
- Relationships between tables
- Validation rules

## Usage with Services

The database service uses this module for database connectivity:

```python
from app.services.database_service import DatabaseService
from app.models.database import SessionLocal

db_service = DatabaseService()
```