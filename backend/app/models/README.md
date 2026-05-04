# Data Models

This directory contains database models and session management.

## Structure

```
models/
├── database.py       # Database session and engine
├── schemas.py        # Shared database models
└── README.md         # This file
```

## Database Connection

`database.py` manages:
- Database engine creation
- Session factory
- Dependency injection for database sessions

## Models

Database models define:
- Table structures
- Relationships between tables
- Validation rules

## Usage

Models are used throughout the application for data persistence:

```python
from app.models.database import get_db
from app.models.schemas import User
```

## Migrations

This project uses Alembic for database migrations (when implemented):
- Migration scripts in `alembic/` directory
- Automatic migration generation
- Safe upgrade/downgrade procedures