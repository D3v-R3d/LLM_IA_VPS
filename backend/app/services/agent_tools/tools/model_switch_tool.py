"""
Tool for listing and switching LLM models.
Uses user preferences to store the selected model.
"""

import httpx
from typing import Any, Dict
from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult
from app.core.config import settings


AVAILABLE_MODELS = [
    {"id": "qwen3.5:397b-cloud", "name": "Qwen 3.5 (Fast)", "description": "Fast, good for simple tasks"},
    {"id": "qwen3.5:32b", "name": "Qwen 3.5 32B", "description": "Balanced speed and quality"},
    {"id": "qwen3.5:72b", "name": "Qwen 3.5 72B", "description": "Higher quality, slower"},
    {"id": "llama3.1:8b", "name": "Llama 3.1 8B", "description": "Open source, fast"},
    {"id": "llama3.1:70b", "name": "Llama 3.1 70B", "description": "High quality open source"},
    {"id": "gemma4:31b", "name": "Gemma 4 31B", "description": "Google's latest, high quality"},
    {"id": "mistral:7b", "name": "Mistral 7B", "description": "Fast, good reasoning"},
]


class ModelSwitchTool(BaseTool):
    """Tool for listing available models and switching the active model."""

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

    async def execute(self, action: str, model_id: str = None, **kwargs) -> ToolResult:
        try:
            if action == "list":
                available = await self._fetch_available_models()
                
                text = "## 🤖 Available Models\n\n"
                for m in available:
                    text += f"- **{m['name']}** (`{m['id']}`)\n"
                    text += f"  {m['description']}\n"
                
                return ToolResult(success=True, data={"models": available, "text": text})
            
            elif action == "switch":
                if not model_id:
                    return ToolResult(success=False, error="model_id required for switch action")
                
                # Query API to verify model exists
                available = await self._fetch_available_models()
                available_ids = [m["id"] for m in available]
                
                if model_id not in available_ids:
                    return ToolResult(
                        success=False, 
                        error=f"Model `{model_id}` not available. Use /model list to see available models."
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
        """Fetch available models from Ollama Cloud API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.OLLAMA_CLOUD_HOST}/api/tags",
                    headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
                )
                if response.status_code == 200:
                    result = response.json()
                    return [
                        {"id": m.get("name"), "name": m.get("name"), "description": "Available on Ollama Cloud"}
                        for m in result.get("models", [])
                    ]
        except Exception:
            pass
        
        return AVAILABLE_MODELS