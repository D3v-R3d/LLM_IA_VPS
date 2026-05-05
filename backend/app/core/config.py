"""
Configuration module for the Tower Project application.

This module defines application settings using Pydantic Settings,
which loads configuration from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
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

    # Ollama local server URL for embeddings
    # When running in Docker, use the service name 'ollama'
    OLLAMA_HOST: str = "http://ollama:11434"

    # Ollama Cloud API URL for chat completions
    OLLAMA_CLOUD_HOST: str = "https://ollama.com"

    # Ollama Cloud API key for authentication
    OLLAMA_API_KEY: Optional[str] = None

    # Telegram Bot configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_SECRET_TOKEN: Optional[str] = "tower_secret_token_change_me"
    TELEGRAM_WEBHOOK_URL: Optional[str] = None


# Global settings instance used throughout the application
# This singleton pattern ensures consistent configuration across all modules
settings = Settings()