# App Package

This is the main application package containing all backend logic.

## Structure

```
app/
├── main.py           # Application entry point
├── api/              # API route definitions
├── core/             # Core application components
├── models/           # Data models
├── schemas/          # Pydantic schemas
├── services/         # Business logic services
├── utils/            # Utility functions
└── README.md         # This file
```

## Entry Point

`main.py` is the application entry point that creates the FastAPI application instance and includes all routers.

## Module Descriptions

- **api**: Contains API route handlers organized by version and resource
- **core**: Core application components like configuration and security
- **models**: Database models and session management
- **schemas**: Pydantic models for request/response validation
- **services**: Business logic implementations and external service integrations
- **utils**: Helper functions used across the application