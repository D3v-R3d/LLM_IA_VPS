import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_event import AgentEvent
from app.observability.event_types import EventLevel, EventType, LEVEL_BY_TYPE
from app.observability.sanitizer import build_payload, sanitize_dict

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Append-only event logger for agent observability.

    Design principles:
    - Fire-and-forget: never blocks agent execution (uses in-memory buffer)
    - Batched writes: accumulate events, flush at end of message journey
    - Extensible: new event types don't require schema changes (JSONB payload)
    - Immutable: only INSERT, no UPDATE/DELETE
    - Sync session: matches existing sync SQLAlchemy pattern in codebase
    """

    def __init__(
        self,
        db: Session,
        run_id: str,
        chat_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        self.db = db
        self.run_id = run_id
        self.chat_id = chat_id
        self.user_id = user_id
        self.agent_id = agent_id
        self._buffer: List[Dict] = []
        self._lock = asyncio.Lock()

    def set_user_id(self, user_id: str) -> None:
        """Update user_id after logger creation (user resolved later in pipeline)."""
        self.user_id = user_id

    def emit(
        self,
        event_type: str,
        event_name: str,
        payload: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_detail: Optional[str] = None,
        step: Optional[str] = None,
        telegram_update_id: Optional[str] = None,
        **extra,
    ) -> uuid.UUID:
        """
        Emit an event synchronously (for sync contexts).

        Returns event ID for correlation.
        """
        event_id = uuid.uuid4()
        full_payload = sanitize_dict({**(payload or {}), **extra})

        event = {
            "id": event_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "telegram_update_id": telegram_update_id,
            "event_type": event_type,
            "event_name": event_name,
            "step": step,
            "payload": full_payload,
            "duration_ms": duration_ms,
            "success": success,
            "error_detail": error_detail,
            "created_at": datetime.utcnow(),
        }

        self._buffer.append(event)
        logger.debug(f"Event buffered: {event_type}/{event_name} (buffer size: {len(self._buffer)})")

        level = LEVEL_BY_TYPE.get(event_type, EventLevel.NORMAL)
        if level in (EventLevel.ERROR, EventLevel.CRITICAL):
            self.flush()

        return event_id

    async def emit_async(
        self,
        event_type: str,
        event_name: str,
        payload: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_detail: Optional[str] = None,
        step: Optional[str] = None,
        telegram_update_id: Optional[str] = None,
        **extra,
    ) -> uuid.UUID:
        """
        Emit an event asynchronously (non-blocking, for async contexts).
        """
        async with self._lock:
            return self.emit(
                event_type=event_type,
                event_name=event_name,
                payload=payload,
                duration_ms=duration_ms,
                success=success,
                error_detail=error_detail,
                step=step,
                telegram_update_id=telegram_update_id,
                **extra,
            )

    def emit_llm_request(
        self,
        model: str,
        provider: str,
        prompt_length: int,
        tools_count: int,
        **extra,
    ) -> uuid.UUID:
        """Convenience: emit LLM_REQUEST event."""
        return self.emit(
            event_type=EventType.LLM_REQUEST,
            event_name="llm_request",
            payload={"model": model, "provider": provider, "prompt_length": prompt_length, "tools_count": tools_count},
            **extra,
        )

    def emit_llm_response(
        self,
        model: str,
        provider: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: int,
        response_preview: Optional[str] = None,
        **extra,
    ) -> uuid.UUID:
        """Convenience: emit LLM_RESPONSE event."""
        return self.emit(
            event_type=EventType.LLM_RESPONSE,
            event_name="llm_response",
            payload={
                "model": model,
                "provider": provider,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "response_preview": response_preview,
            },
            duration_ms=duration_ms,
            **extra,
        )

    def emit_tool_call(
        self,
        tool_name: str,
        call_id: str,
        arguments: Optional[Dict[str, Any]] = None,
        **extra,
    ) -> uuid.UUID:
        """Convenience: emit TOOL_CALL event."""
        sanitized_args = sanitize_dict(arguments) if arguments else {}
        return self.emit(
            event_type=EventType.TOOL_CALL,
            event_name=f"tool_call::{tool_name}",
            payload={"tool_name": tool_name, "call_id": call_id, "arguments": sanitized_args},
            **extra,
        )

    def emit_tool_result(
        self,
        tool_name: str,
        call_id: str,
        success: bool,
        duration_ms: int,
        result_size: int = 0,
        error: Optional[str] = None,
        **extra,
    ) -> uuid.UUID:
        """Convenience: emit TOOL_RESULT event."""
        return self.emit(
            event_type=EventType.TOOL_RESULT,
            event_name=f"tool_result::{tool_name}",
            payload={"tool_name": tool_name, "call_id": call_id, "success": success, "result_size": result_size},
            duration_ms=duration_ms,
            success=success,
            error_detail=error,
            **extra,
        )

    def emit_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        **extra,
    ) -> uuid.UUID:
        """Convenience: emit ERROR event with immediate flush."""
        return self.emit(
            event_type=EventType.ERROR,
            event_name=f"error::{error_type}",
            payload={"error_type": error_type, "stack_trace": stack_trace},
            success=False,
            error_detail=error_message,
            **extra,
        )

    def flush(self) -> int:
        """
        Flush buffered events to DB.

        Returns number of events flushed.
        """
        if not self._buffer:
            return 0

        count = len(self._buffer)
        try:
            self.db.bulk_insert_mappings(AgentEvent, self._buffer)
            self.db.commit()
            logger.info(f"EventLogger: flushed {count} events for run_id={self.run_id}")
        except Exception as e:
            logger.error(f"EventLogger: failed to flush {count} events: {e}")
            self.db.rollback()
        finally:
            self._buffer.clear()

        return count

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)