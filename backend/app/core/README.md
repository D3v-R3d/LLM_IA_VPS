# Core Components

This directory contains core application components.

## Structure

```
core/
├── config.py         # Application configuration
├── security.py       # Security utilities
└── README.md         # This file
```

## Configuration

`config.py` handles application configuration using:
- Environment variables
- Default values
- Type validation with Pydantic Settings

## Security

`security.py` contains security-related utilities:
- Password hashing
- JWT token generation and validation
- Authentication middleware
- Authorization checks

## Usage

Core components are imported and used throughout the application:

```python
from app.core.config import settings
from app.core.security import create_access_token
```