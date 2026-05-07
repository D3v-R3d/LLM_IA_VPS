"""
Configuration module for the Tower Project application.

This module defines application settings using Pydantic Settings,
which loads configuration from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env" if os.path.exists(".env") else None,
        case_sensitive=True,
        extra="ignore",
        env_file_encoding="utf-8"
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

    # Default model name for LLM interactions
    OLLAMA_MODEL: str = "qwen3.5:397b-cloud"

    # Telegram Bot configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_SECRET_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None

    # JWT configuration for authentication
    JWT_SECRET: str = "change_me_in_production_with_strong_secret_key"


def get_settings() -> "Settings":
    """Get settings fresh to pick up environment variable changes (useful for testing)."""
    return Settings()


# Global settings instance used throughout the application
# This singleton pattern ensures consistent configuration across all modules
settings = Settings()