# Tower Project - LLM Application

This project implements a full-stack application for working with Large Language Models (LLMs) using Ollama Cloud, embedding services, and data storage.

## Architecture Overview

The application consists of:
- **Frontend**: React application for user interface
- **Backend**: FastAPI application for API endpoints and LLM integration
- **Database**: PostgreSQL for structured data storage
- **Vector Store**: Qdrant for embedding storage and similarity search
- **Reverse Proxy**: Traefik for routing and SSL termination

## Project Structure

```
tower_project/
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── core/            # Configuration (config.py)
│   │   ├── models/          # Database models (database.py)
│   │   ├── services/        # Business logic services
│   │   │   ├── llm_service.py         # Ollama Cloud integration
│   │   │   ├── qdrant_service.py     # Qdrant operations
│   │   │   └── database_service.py  # PostgreSQL operations
│   │   └── main.py          # Application entry point
│   └── requirements.txt
├── frontend/                 # React frontend application
├── docker/                    # Docker configurations
├── docker-compose.yml         # Docker Compose configuration
└── README.md                 # This file
```

## Services Configuration

### Backend Configuration
The backend connects to three external services configured via environment variables:

- **DATABASE_URL**: `postgresql://postgres:password@postgres:5432/tower_db`
- **QDRANT_URL**: `http://qdrant:6333`
- **OLLAMA_API_BASE**: `https://ollama.com`

### Health Check Endpoints

The backend provides health check endpoints for monitoring:

- `GET /health` - Overall application health
- `GET /health/database` - PostgreSQL health status
- `GET /health/qdrant` - Qdrant vector database health status
- `GET /health/ollama` - Ollama Cloud API health status

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Ollama Cloud account (for LLM inference)
- Domain names configured to point to your server (optional)

### Running the Application

1. Start all services:

```bash
docker-compose up -d --build
```

2. Check service health:

```bash
# Main health check
curl http://localhost:8000/health

# Individual service checks
curl http://localhost:8000/health/database
curl http://localhost:8000/health/qdrant
curl http://localhost:8000/health/ollama
```

### Accessing Services

After deployment with Traefik:
- **Frontend**: https://www.srv1632761.hstgr.cloud
- **Backend API**: https://api.srv1632761.hstgr.cloud/api
- **Qdrant Dashboard**: https://api.srv1632761.hstgr.cloud/qdrant

## Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## API Documentation

When running locally, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker Services

### PostgreSQL
- **Container**: tower_postgres
- **Port**: 5432
- **Database**: tower_db
- **Credentials**: postgres/password

### Qdrant (Vector Database)
- **Container**: tower_qdrant
- **Ports**: 6333 (REST), 6334 (gRPC)
- **Data Volume**: qdrant_data

### Backend (FastAPI)
- **Container**: tower_backend
- **Port**: 8000
- **Framework**: Uvicorn

### Frontend (React)
- **Container**: tower_frontend
- **Port**: 3000
- **Server**: serve (static file serving)

## Deployment Notes

Traefik is expected to be running separately with the following configuration:
- Listening on ports 80 and 443
- Using Let's Encrypt for SSL certificates
- Configured with appropriate entrypoints and certificate resolvers

The services in this project automatically register with Traefik through Docker labels.