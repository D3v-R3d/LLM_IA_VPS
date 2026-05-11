class EventType:
    AGENT_START = "agent_start"
    AGENT_STEP = "agent_step"
    AGENT_END = "agent_end"

    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"

    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

    DECISION = "decision"

    ERROR = "error"
    CRITICAL = "critical"

    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"

    SYSTEM = "system_event"

    TELEGRAM_RECEIVED = "telegram_received"
    TELEGRAM_PARSED = "telegram_parsed"
    TELEGRAM_SENT = "telegram_sent"

    USER_RESOLVED = "user_resolved"
    ACCOUNT_NOT_LINKED = "account_not_linked"

    SESSION_RESOLVED = "session_resolved"

    RATE_LIMITED = "rate_limited"
    LOCK_ACQUIRED = "lock_acquired"

    PLAN_GENERATED = "plan_generated"

    SYNTHESIS = "synthesis"


class EventLevel:
    NORMAL = "normal"
    ERROR = "error"
    CRITICAL = "critical"


LEVEL_BY_TYPE = {
    EventType.ERROR: EventLevel.ERROR,
    EventType.CRITICAL: EventLevel.CRITICAL,
}