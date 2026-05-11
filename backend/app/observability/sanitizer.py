import re
import uuid
from typing import Any, Dict, List


SENSITIVE_KEYS = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "api-key",
    "apikey",
    "access_token",
    "access-token",
    "refresh_token",
    "refresh-token",
    "authorization",
    "auth",
    "bearer",
    "credential",
    "private_key",
    "private-key",
    "session_id",
    "sessionid",
    "csrf_token",
    "csrftoken",
    "x_api_key",
    "x-api-key",
})


def _coerce_uuid(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("-", "_").replace(" ", "_")
    if key_lower in SENSITIVE_KEYS:
        return True
    for sensitive in SENSITIVE_KEYS:
        if sensitive in key_lower:
            return True
    return False


def sanitize_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "***"
    return _coerce_uuid(value)


def truncate_field(field_name: str, value: Any, limit: int) -> tuple[Any, bool]:
    if not isinstance(value, str):
        value = str(value)
    if len(value) <= limit:
        return value, False
    return value[:limit], True


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return _coerce_uuid(data)
    result = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            result[key] = "***"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item) if isinstance(item, dict) else _coerce_uuid(item)
                for item in value
            ]
        else:
            result[key] = _coerce_uuid(value)
    return result


def build_payload(
    event_name: str,
    data: Dict[str, Any],
    truncate_limits: Dict[str, int] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if truncate_limits is None:
        truncate_limits = TRUNCATE_LIMITS

    meta = {}
    payload = {}

    for key, value in data.items():
        value = _coerce_uuid(value)
        if key in truncate_limits:
            original_len = len(value) if isinstance(value, str) else 0
            limited_value, truncated = truncate_field(key, value, truncate_limits[key])
            payload[key] = limited_value
            if truncated:
                meta[key] = {"truncated": True, "original_size": original_len}
        else:
            payload[key] = value

    return payload, meta