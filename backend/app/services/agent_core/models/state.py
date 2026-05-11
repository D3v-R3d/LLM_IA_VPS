from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json

from app.services.agent_core.models.plan import Plan


def generate_call_key(tool_call: Dict) -> str:
    """Generate unique key for tool call (name + arguments)."""
    name = tool_call.get("function", {}).get("name", "")
    args = tool_call.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    key_data = f"{name}:{json.dumps(args, sort_keys=True)}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


@dataclass
class RunState:
    """
    Track execution state through the loop.
    Includes tool_history for loop detection, retry tracking, and idempotency.
    """
    iteration: int = 0
    total_retries: int = 0
    step_retries: int = 0
    completed_tools: List[str] = field(default_factory=list)
    failed_tools: List[str] = field(default_factory=list)
    tool_history: List[str] = field(default_factory=list)
    tool_call_counts: Dict[str, int] = field(default_factory=dict)
    plan: Optional[Plan] = None
    last_tool_result_success: bool = True
    executed_calls: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    result_signatures: List[str] = field(default_factory=list)
    run_id: Optional[str] = None


def detect_loop_v2(
    tool_history: List[str],
    tool_call_counts: Dict[str, int],
    window_size: int = 5,
    max_consecutive: int = 3
) -> Optional[str]:
    """
    Detect loop using sliding window + frequency + whitelist.
    Returns tool name if loop detected, None otherwise.
    """
    if not tool_history or len(tool_history) < 3:
        return None

    whitelist = {"ls", "dir", "list", "search", "grep", "find", "web_search", "read_file"}

    recent = tool_history[-window_size:]

    consecutive = 0
    last_tool = None
    for tool in reversed(recent):
        if tool == last_tool:
            consecutive += 1
        else:
            consecutive = 1
            last_tool = tool
        if consecutive >= max_consecutive:
            if tool not in whitelist:
                return tool
            elif len(recent) >= max_consecutive + 2:
                return tool

    if len(recent) >= 3:
        most_common = max(set(recent), key=recent.count)
        frequency = recent.count(most_common) / len(recent)
        if frequency > 0.6:
            if most_common not in whitelist or len(recent) >= window_size:
                return most_common

    return None


def should_retry(tool_name: str, retry_counts: Dict[str, int], max_retries: int = 2) -> bool:
    """Check if tool should be retried based on retry count."""
    return retry_counts.get(tool_name, 0) < max_retries