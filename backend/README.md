# Backend - FastAPI Application

This directory contains the backend application built with FastAPI.

## Structure

```
backend/
├── app/              # Main application package
├── tests/            # Test suite
├── Dockerfile        # Docker configuration
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Main Components

- `app/main.py`: Application entry point
- `app/api/`: API route handlers
- `app/core/`: Core application components
- `app/models/`: Data models and database interactions
- `app/schemas/`: Pydantic schemas for request/response validation
- `app/services/`: Business logic and external service integrations
- `app/utils/`: Utility functions

## Development

To run the backend locally for development:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## API Documentation

When running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Dependencies

Main dependencies include:
- FastAPI: Web framework
- SQLAlchemy: ORM for database interactions
- AsyncPG: PostgreSQL driver
- Qdrant-client: Vector database client
- Pydantic: Data validation