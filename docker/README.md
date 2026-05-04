# Docker Configuration

This directory contains Docker-related configuration files and documentation.

## Overview

The main Docker configuration is defined in the root `docker-compose.yml` file. This directory can be used for additional Docker configurations, such as:

- Custom Dockerfiles for specific services
- Docker network configurations
- Docker volume configurations
- Environment-specific overrides

## Docker Compose Services

The main `docker-compose.yml` defines the following services:

1. **backend** - FastAPI application
2. **frontend** - React application
3. **postgres** - PostgreSQL database
4. **qdrant** - Vector database

## Networks

Services are connected through a custom bridge network called `tower_network` which allows them to communicate with each other while isolating them from other Docker containers.

## Volumes

Persistent data is stored in Docker volumes:
- `postgres_data`: PostgreSQL database files
- `qdrant_data`: Qdrant vector database files

## Traefik Integration

Services are automatically discovered and routed by Traefik through Docker labels defined in the `docker-compose.yml` file.

## Customization

To customize the Docker configuration:

1. Modify the services in `docker-compose.yml`
2. Adjust environment variables as needed
3. Add new services if required
4. Update Traefik labels for new services

## Commands

Common Docker Compose commands:

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs

# Restart a specific service
docker-compose restart backend
```