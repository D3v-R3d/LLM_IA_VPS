"""
Tool Registry (Refactored)

Central registry for all available tools.
Auto-discovers tools from tools/ subdirectories.
Thread-safe singleton.
"""

import importlib
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Type

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.schemas import validate_canonical_tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry that holds all available tools.
    Tools are indexed by name for quick lookup.
    Thread-safe singleton.
    """
    
    _instance: Optional["ToolRegistry"] = None
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_names: List[str] = []
        self._discover()
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _discover(self):
        """
        Auto-discover tools from tools/ subdirectories.
        Scans for Python files, imports modules, finds BaseTool subclasses.
        """
        # Base path: app/services/agent_tools/tools/
        base_path = Path(__file__).parent.parent / "tools"
        if not base_path.exists():
            logger.warning(f"Tools directory not found: {base_path}")
            return
        
        # Walk through category subdirectories (file/, system/, web/, memory/, etc.)
        for category_dir in base_path.iterdir():
            if not category_dir.is_dir():
                continue
            if category_dir.name.startswith('_'):
                continue
            
            # Import all .py files in this category directory
            for py_file in category_dir.glob("*.py"):
                if py_file.name.startswith('_'):
                    continue
                
                # Convert file path to module path
                rel_path = py_file.relative_to(Path(__file__).parent.parent.parent.parent)
                module_path = ".".join(rel_path.with_suffix("").parts)
                
                try:
                    module = importlib.import_module(module_path)
                except Exception as e:
                    logger.error(f"Failed to import {module_path}: {e}")
                    continue
                
                # Find BaseTool subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseTool) and 
                        attr is not BaseTool and
                        attr is not BaseTool.__subclasses__()):  # exclude intermediate classes
                        
                        # Instantiate and register
                        try:
                            tool_instance = attr()
                            self.register(tool_instance)
                            logger.info(f"Discovered tool: {tool_instance.name} from {module_path}")
                        except Exception as e:
                            logger.error(f"Failed to instantiate {attr_name} from {module_path}: {e}")
        
        # Also import tools from the old monolithic files (for backward compatibility)
        self._register_legacy_tools()
    
    def _register_legacy_tools(self):
        """Register tools from old monolithic files (temporary)."""
        legacy_modules = [
            "app.services.agent_tools.tools.file_tools",
            "app.services.agent_tools.tools.system_tools",
            "app.services.agent_tools.tools.web_tools",
            "app.services.agent_tools.tools.database_tools",
            "app.services.agent_tools.tools.telegram_tools",
            "app.services.agent_tools.tools.nas_tools",
            "app.services.agent_tools.tools.scraper_tools",
            "app.services.agent_tools.tools.model_switch_tool",
            "app.services.agent_tools.tools.qdrant_tools",
            "app.services.agent_tools.tools.user_notes_tool",
            "app.services.agent_tools.tools.web_search",
            "app.services.agent_tools.tools.url_fetch",
            "app.services.agent_tools.tools.api_caller",
        ]
        
        for module_path in legacy_modules:
            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                logger.warning(f"Could not import legacy module {module_path}: {e}")
                continue
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseTool) and 
                    attr is not BaseTool):
                    
                    try:
                        tool_instance = attr()
                        # Check if already registered (avoid duplicates)
                        if tool_instance.name not in self._tools:
                            self.register(tool_instance)
                            logger.info(f"Registered legacy tool: {tool_instance.name}")
                    except Exception as e:
                        logger.error(f"Failed to instantiate legacy tool {attr_name}: {e}")
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        if tool.name not in self._tool_names:
            self._tool_names.append(tool.name)
    
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool by name."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            self._tool_names.remove(tool_name)
            return True
        return False
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_all_canonical(self) -> List[Dict]:
        """Get canonical schemas for ALL tools."""
        return [tool.to_canonical() for tool in self._tools.values()]
    
    def get_definitions_by_names(self, names: List[str]) -> List[Dict]:
        """Get OpenAI-style definitions for specific tools by name."""
        return [
            tool.to_definition()
            for name in names
            for tool in [self._tools.get(name)]
            if tool is not None
        ]
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def list_names(self) -> List[str]:
        """List all tool names."""
        return self._tool_names.copy()
    
    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")
        
        # Optional: validate arguments
        validation_error = tool.validate_args(**kwargs)
        if validation_error:
            return ToolResult(success=False, error=f"Validation error: {validation_error}")
        
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}: {e}")
            return ToolResult(success=False, error=f"Tool execution failed: {str(e)}")
    
    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools>"


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return ToolRegistry.get_instance()


def get_tool_definitions() -> List[Dict]:
    """Get all tool definitions for LLM function calling (OpenAI format)."""
    return get_registry().get_all_definitions()


# For backward compatibility with old imports
def get_all_tools() -> List[BaseTool]:
    """Get all tools (legacy)."""
    return get_registry().get_all()
