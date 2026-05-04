"""
Configuration module for the Tower Project application.

This module defines application settings using Pydantic Settings,
which loads configuration from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: PostgreSQL connection string in the format:
                      postgresql://user:password@host:port/database
        QDRANT_URL: Qdrant vector database server URL
        OLLAMA_HOST: Ollama Cloud API base URL for LLM interactions
        OLLAMA_API_KEY: API key for Ollama Cloud authentication
    """

    # Default PostgreSQL connection string
    # Uses docker service name 'postgres' as hostname when running in Docker
    DATABASE_URL: str = "postgresql://postgres:password@postgres:5432/tower_db"

    # Default Qdrant server URL (runs as Docker service named 'qdrant')
    QDRANT_URL: str = "http://qdrant:6333"

    # Ollama Cloud API base URL
    # Note: Ollama Cloud provides LLM inference through this endpoint
    OLLAMA_HOST: str = "https://ollama.com"

    # Ollama Cloud API key for authentication
    # Get your API key from https://ollama.com/account
    OLLAMA_API_KEY: Optional[str] = None

    class Config:
        # Load environment variables from .env file if present
        env_file = ".env"

        # Ensure environment variable names match exactly (case-sensitive)
        case_sensitive = True


# Global settings instance used throughout the application
# This singleton pattern ensures consistent configuration across all modules
settings = Settings()