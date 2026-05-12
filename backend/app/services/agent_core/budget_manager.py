"""
Budget Manager

Pre-execution budget checking for tool calls.
Returns filtered tool calls or logs warnings when budget exhausted.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BudgetManager:
    """
    Pre-execution budget checking.
    Returns filtered tool calls or None if budget exhausted.
    """

    def __init__(self, budgets: Optional[Dict[str, int]] = None):
        self._budgets = budgets or {}
        self._initial = budgets.copy() if budgets else {}

    def check(self, tool_calls: List[Dict]) -> List[Dict]:
        """Check budgets and return filtered tool_calls."""
        filtered = []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name")
            if name in self._budgets:
                if self._budgets[name] > 0:
                    self._budgets[name] -= 1
                    filtered.append(tc)
                else:
                    logger.warning(f"BUDGET_EXHAUSTED: {name}")
            else:
                filtered.append(tc)
        return filtered

    def get_exhausted_tools(self) -> List[str]:
        return [
            name for name, remaining in self._budgets.items()
            if remaining <= 0
        ]

    def get_remaining(self, tool_name: str) -> int:
        return self._budgets.get(tool_name, -1)

    def reset(self):
        """Reset budgets to initial state."""
        self._budgets = self._initial.copy()