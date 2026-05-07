"""
Context Service Module

Simple wrapper that imports compression logic from context_compression.py
"""

from app.services.context_compression import (
    ContextCompressionService,
    compression_service,
    CONTEXT_CONFIG,
)

ContextService = ContextCompressionService

context_service = compression_service
