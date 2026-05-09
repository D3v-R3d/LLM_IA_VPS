"""
LLM Logger Service

Logs LLM interactions to the database for analysis and debugging.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.llm_log import LlmLog

logger = logging.getLogger(__name__)


class LlmLogger:
    """Service for logging LLM interactions."""

    def __init__(self, db: Session):
        self.db = db

    def log_request(
        self,
        message: str,
        model: str,
        provider: str,
        user_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        chat_id: Optional[str] = None,
        tools_sent: Optional[List[Dict[str, Any]]] = None,
        intent: Optional[str] = None,
    ) -> uuid.UUID:
        """
        Log the start of an LLM request.

        Returns:
            log_id: UUID of the created log entry
        """
        log_entry = LlmLog(
            user_id=user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
            message=message,
            response_text=None,
            model=model,
            provider=provider,
            tools_sent=tools_sent,
            tool_calls=None,
            tokens_input=None,
            tokens_output=None,
            duration_ms=None,
            iterations=1,
            intent=intent,
            success=True,
            error=None,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        logger.debug(f"LLM request logged: id={log_entry.id}, model={model}")
        return log_entry.id

    def log_response(
        self,
        log_id: uuid.UUID,
        response_text: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        duration_ms: Optional[int] = None,
        iterations: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        error_body: Optional[str] = None,
        error_url: Optional[str] = None,
    ) -> None:
        """
        Log the response from an LLM request.

        Args:
            log_id: UUID from log_request()
            response_text: LLM response content
            tool_calls: Tools called by LLM
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            duration_ms: Total duration in milliseconds
            iterations: Number of LLM iterations
            success: Whether the call succeeded
            error: Error message if failed
            error_code: HTTP status code (e.g., 500, 429)
            error_body: Full error response body
            error_url: URL that failed
        """
        log_entry = self.db.query(LlmLog).filter(LlmLog.id == log_id).first()
        if not log_entry:
            logger.warning(f"LLM log not found: {log_id}")
            return

        log_entry.response_text = response_text
        log_entry.tool_calls = tool_calls
        log_entry.tokens_input = tokens_input
        log_entry.tokens_output = tokens_output
        log_entry.duration_ms = duration_ms
        if iterations:
            log_entry.iterations = iterations
        log_entry.success = success
        log_entry.error = error
        log_entry.error_code = error_code
        log_entry.error_body = error_body
        log_entry.error_url = error_url

        self.db.commit()
        logger.debug(f"LLM response logged: id={log_id}, success={success}, duration={duration_ms}ms")

    def update_iterations(self, log_id: uuid.UUID, iterations: int) -> None:
        """Update the iteration count for a log entry."""
        log_entry = self.db.query(LlmLog).filter(LlmLog.id == log_id).first()
        if log_entry:
            log_entry.iterations = iterations
            self.db.commit()


def create_llm_logger(db: Session) -> LlmLogger:
    """Factory function to create LlmLogger instance."""
    return LlmLogger(db)