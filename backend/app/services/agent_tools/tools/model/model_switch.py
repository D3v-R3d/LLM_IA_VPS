"""
Model switch tool.
"""

from typing import Any, Dict

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.providers.llm.provider_factory import provider_factory
from app.core.config import settings


class ModelSwitchTool(BaseTool):
    """Tool for listing available models and switching the active model."""

    META = {"category": "util", "max_calls_per_run": 0, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "model_switch"

    @property
    def description(self) -> str:
        return "List available LLM models or switch to a different model. Use 'list' to see available models or 'switch:model_id' to change."

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "switch"],
                    "description": "Action to perform: 'list' to see models, 'switch' to change model"
                },
                "model_id": {
                    "type": "string",
                    "description": "Model ID to switch to (required for 'switch' action)"
                }
            },
            "required": ["action"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        model_id = kwargs.get("model_id")

        if not action:
            return ToolResult(success=False, error="Missing action")

        try:
            if action == "list":
                available = await self._fetch_available_models()

                text = "## Available Models\n\n"
                for m in available:
                    text += f"- **{m['name']}** (`{m['id']}`)\n"
                    text += f"  {m['description']}\n"

                return ToolResult(success=True, data={"models": available, "text": text})

            elif action == "switch":
                if not model_id:
                    return ToolResult(success=False, error="model_id required for switch action")

                available = await self._fetch_available_models()
                available_ids = [m["id"] for m in available]

                if model_id not in available_ids:
                    return ToolResult(
                        success=False,
                        error=f"Model `{model_id}` not available. Use model switch list to see available models."
                    )

                return ToolResult(
                    success=True,
                    data={
                        "model_id": model_id,
                        "text": f"Model switched to `{model_id}`. This will be saved to your preferences."
                    }
                )

            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _fetch_available_models(self) -> list:
        """Fetch available models from the current LLM provider."""
        try:
            provider = provider_factory.get_provider(settings.LLM_PROVIDER)
            models = await provider.list_models()
            return [
                {"id": m.get("id") or m.get("name") or m.get("model", ""),
                 "name": m.get("name") or m.get("id") or m.get("model", ""),
                 "description": f"Available on {provider.name}"}
                for m in models
            ]
        except Exception:
            pass

        return []