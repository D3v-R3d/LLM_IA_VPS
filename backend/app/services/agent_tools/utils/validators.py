"""
Validators

Parameter and schema validation utilities.
"""

from typing import Dict, Any, Optional
import json


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
    """
    Validate data against a JSON Schema.
    Returns error string if invalid, None if valid.
    Uses jsonschema library if available, otherwise basic checks.
    """
    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return None
    except ImportError:
        # Fallback: basic validation
        return _basic_validate(data, schema)
    except Exception as e:
        return str(e)


def _basic_validate(data: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
    """Basic validation without jsonschema."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    # Check required fields
    for field in required:
        if field not in data:
            return f"Missing required field: {field}"
    
    # Check types (very basic)
    for field, value in data.items():
        if field in properties:
            expected_type = properties[field].get("type")
            if expected_type and not _check_type(value, expected_type):
                return f"Field {field} should be of type {expected_type}"
    
    return None


def _check_type(value: Any, expected_type: str) -> bool:
    """Check if value matches expected JSON Schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    if expected_type in type_map:
        return isinstance(value, type_map[expected_type])
    return True  # Unknown type, assume ok


def validate_tool_args(tool_params: Dict[str, Any], **kwargs) -> Optional[str]:
    """Validate tool arguments against tool's parameters schema."""
    return validate_schema(kwargs, tool_params)
