"""
Agent Core - Refactored Architecture

Components:
- AgentRunner: Simple stateless agent runner (ACTIVE - used by ChatOrchestrator)
- ToolExecutor: Independent tool execution layer
- ContextBuilder: Centralized context building
- Side systems: TelegramNotifier, BudgetManager, ConvergenceAnalyzer, MetricsCollector
"""

from app.services.agent_core.runner import AgentRunner
from app.services.agent_core.tool_executor import ToolExecutor
from app.services.agent_core.context_builder import ContextBuilder, AgentContext, get_context_builder
from app.services.agent_core.side_systems import (
    TelegramNotifier,
    BudgetManager,
    ConvergenceAnalyzer,
    MetricsCollector,
)

__all__ = [
    "AgentRunner",
    "ToolExecutor",
    "ContextBuilder",
    "AgentContext",
    "get_context_builder",
    "TelegramNotifier",
    "BudgetManager",
    "ConvergenceAnalyzer",
    "MetricsCollector",
]