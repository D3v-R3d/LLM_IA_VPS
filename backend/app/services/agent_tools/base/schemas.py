"""
Canonical Tool Schema

Single source of truth for tool definitions across all providers.
All tools must produce/consume this schema.
"""

from typing import Dict, Any

# Canonical schema for a tool (internal representation)
CANONICAL_TOOL_SCHEMA = {
    "name": str,           # Unique tool identifier
    "description": str,     # Human-readable description
    "parameters": dict,     # JSON Schema for parameters
    "meta": {               # Internal metadata (NOT sent to LLM)
        "category": str,         # "file", "system", "web", "memory", etc.
        "max_calls_per_run": int, # 0 = unlimited
        "parallel_safe": bool,
    }
}

# Provider-specific format types
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_GOOGLE = "google"
PROVIDER_GROQ = "groq"
PROVIDER_OLLAMA = "ollama"


def validate_canonical_tool(tool_dict: Dict[str, Any]) -> bool:
    """Validate that a dict matches the canonical schema."""
    required_keys = ["name", "description", "parameters", "meta"]
    for key in required_keys:
        if key not in tool_dict:
            return False
    
    meta = tool_dict.get("meta", {})
    if not isinstance(meta, dict):
        return False
    
    meta_required = ["category", "max_calls_per_run", "parallel_safe"]
    for key in meta_required:
        if key not in meta:
            return False
    
    return True


def to_openai_format(tools: list) -> list:
    """Convert canonical tools to OpenAI function-calling format."""
    result = []
    for tool in tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
        })
    return result


def to_anthropic_format(tools: list) -> list:
    """Convert canonical tools to Anthropic tool format."""
    result = []
    for tool in tools:
        result.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        })
    return result


def to_google_format(tools: list) -> list:
    """Convert canonical tools to Google Gemini function_declarations format."""
    result = []
    for tool in tools:
        result.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        })
    return [{"function_declarations": result}]
