"""
Configuration module for the Tower Project application.

This module defines application settings using Pydantic Settings,
which loads configuration from environment variables.
"""

import os
from typing import Optional


def _read_secret_file(filepath: str) -> Optional[str]:
    """Read a secret from a Docker secret file."""
    if filepath and os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return None


class Settings:
    """Application settings with support for Docker secrets."""

    def __init__(self):
        self.DATABASE_URL = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:password@postgres:5432/tower_db"
        )
        self.QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
        self.OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.OLLAMA_CLOUD_HOST = os.environ.get("OLLAMA_CLOUD_HOST", "https://ollama.com")
        self.LLM_MODEL = os.environ.get("LLM_MODEL", "")
        self.OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "")

        self.OLLAMA_API_KEY = (
            os.environ.get("OLLAMA_API_KEY") or
            _read_secret_file(os.environ.get("OLLAMA_API_KEY_FILE", ""))
        )
        self.GROQ_API_KEY = (
            os.environ.get("GROQ_API_KEY") or
            _read_secret_file(os.environ.get("GROQ_API_KEY_FILE", ""))
        )
        self.GOOGLE_API_KEY = (
            os.environ.get("GOOGLE_API_KEY") or
            _read_secret_file(os.environ.get("GOOGLE_API_KEY_FILE", ""))
        )
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "google")
        self.TELEGRAM_BOT_TOKEN = (
            os.environ.get("TELEGRAM_BOT_TOKEN") or
            _read_secret_file(os.environ.get("TELEGRAM_BOT_TOKEN_FILE", ""))
        )
        self.TELEGRAM_BOT_USERNAME = (
            os.environ.get("TELEGRAM_BOT_USERNAME") or
            _read_secret_file(os.environ.get("TELEGRAM_BOT_USERNAME_FILE", ""))
        )
        self.TELEGRAM_SECRET_TOKEN = (
            os.environ.get("TELEGRAM_SECRET_TOKEN") or
            _read_secret_file(os.environ.get("TELEGRAM_SECRET_TOKEN_FILE", ""))
        )
        self.TELEGRAM_WEBHOOK_URL = os.environ.get("TELEGRAM_WEBHOOK_URL")
        self.JWT_SECRET = (
            os.environ.get("JWT_SECRET") or
            _read_secret_file(os.environ.get("JWT_SECRET_FILE", "")) or
            "change_me_in_production_with_strong_secret_key"
        )
        self.PROMPT_DIR = os.environ.get("PROMPT_DIR", "/home/projects/tower_project/prompt")


def get_settings() -> "Settings":
    """Get settings instance."""
    return Settings()


# Global settings instance used throughout the application
settings = Settings()