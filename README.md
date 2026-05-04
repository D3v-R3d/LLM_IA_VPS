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
├── backend/          # FastAPI backend application
├── frontend/         # React frontend application
├── docker/           # Docker configurations
├── docs/             # Documentation files
├── docker-compose.yml # Docker Compose configuration
└── README.md         # This file
```

## Prerequisites

- Docker and Docker Compose
- Ollama installed and running locally (for LLM inference)
- Domain names configured to point to your server

## Getting Started

1. Clone this repository
2. Update the domain names in `docker-compose.yml` to match your domain
3. Ensure Ollama is running on your host machine
4. Run the application:

```bash
docker-compose up -d
```

## Services

- **Frontend**: http://www.yourdomain.com
- **Backend API**: http://api.yourdomain.com/api
- **Qdrant Dashboard**: http://api.yourdomain.com/qdrant

## Configuration

Environment variables can be set in the `docker-compose.yml` file or through a `.env` file.

## Deployment Notes

Traefik is expected to be running separately with the following configuration:
- Listening on ports 80 and 443
- Using Let's Encrypt for SSL certificates
- Configured with appropriate entrypoints and certificate resolvers

The services in this project automatically register with Traefik through Docker labels.