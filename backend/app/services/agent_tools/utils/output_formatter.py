"""
Output Formatter

Normalize ToolResult for LLM consumption.
"""

from typing import Any, Dict
from app.services.agent_tools.base.base_tool import ToolResult


def format_tool_result(result: ToolResult) -> str:
    """
    Convert ToolResult to a string suitable for LLM context.
    
    Success: returns formatted data (json string, summary, etc.)
    Failure: returns error message.
    """
    if result.success:
        data = result.data
        if data is None:
            return "(no output)"
        if isinstance(data, (dict, list)):
            import json
            try:
                return json.dumps(data, ensure_ascii=False, indent=2)
            except:
                return str(data)
        return str(data)
    else:
        error = result.error or "Unknown error"
        return f"Tool error: {error}"


def format_tool_result_dict(result: ToolResult) -> Dict[str, Any]:
    """
    Convert ToolResult to a dict (for structured output).
    """
    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "formatted": format_tool_result(result),
    }


def format_multiple_results(results: list) -> str:
    """Format multiple ToolResults into a single string."""
    parts = []
    for i, res in enumerate(results):
        if isinstance(res, ToolResult):
            part = format_tool_result(res)
        else:
            part = str(res)
        parts.append(f"[Tool {i+1}]\n{part}")
    return "\n\n".join(parts)
