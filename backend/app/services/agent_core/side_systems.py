"""
Side systems that run OUTSIDE the agent loop.
All are async workers or post-processing components.
"""

import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================
# 1. TELEGRAM NOTIFIER (Async Worker)
# ============================================================

class TelegramNotifier:
    """
    Async notification worker.
    NEVER blocks the agent loop.
    """

    def __init__(self, telegram_service, semaphore_limit: int = 5):
        self.telegram_service = telegram_service
        self.sem = asyncio.Semaphore(semaphore_limit)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self):
        """Start background worker."""
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._worker())
        logger.info("TelegramNotifier started")

    async def stop(self):
        """Stop the worker."""
        self._running = False

    async def _worker(self):
        """Background worker that processes notifications."""
        while self._running:
            try:
                chat_id, tool_name, result = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                await self._send_notification(chat_id, tool_name, result)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"TelegramNotifier error: {e}")

    async def notify(
        self,
        chat_id: str,
        tool_name: str,
        result: Dict,
    ):
        """Non-blocking notification request."""
        if not self._running:
            return
        try:
            await asyncio.wait_for(
                self._queue.put((chat_id, tool_name, result)),
                timeout=0.1
            )
        except asyncio.QueueFull:
            logger.warning("TelegramNotifier queue full, dropping notification")

    async def _send_notification(
        self,
        chat_id: str,
        tool_name: str,
        result: Dict,
    ):
        async with self.sem:
            try:
                if result.get("success"):
                    preview = str(result.get("data", ""))[:200]
                    await self.telegram_service.send_message(
                        chat_id,
                        f"✓ {tool_name}: {preview}"
                    )
                else:
                    error = str(result.get("error", ""))[:200]
                    await self.telegram_service.send_message(
                        chat_id,
                        f"❌ {tool_name}: {error}"
                    )
            except Exception as e:
                logger.error(f"Send notification failed: {e}")


# ============================================================
# 2. BUDGET MANAGER (Pre-execution Policy)
# ============================================================

class BudgetManager:
    """
    Pre-execution budget checking.
    Returns filtered tool calls or None if budget exhausted.
    """

    def __init__(self, budgets: Optional[Dict[str, int]] = None):
        # budgets: {"web_search": 3, "bash": 2, ...}
        self._budgets = budgets or {}
        self._initial = budgets.copy() if budgets else {}

    def check(
        self,
        tool_calls: List[Dict],
    ) -> List[Dict]:
        """
        Check budgets and return filtered tool_calls.
        Logs warnings for exhausted tools.
        """
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
        return self._budgets.get(tool_name, -1)  # -1 means no budget defined

    def reset(self):
        """Reset budgets to initial state."""
        self._budgets = self._initial.copy()


# ============================================================
# 3. CONVERGENCE ANALYZER (Post-execution)
# ============================================================

class ConvergenceAnalyzer:
    """
    Post-execution convergence detection.
    Compares signatures to detect loops.
    """

    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self._previous_signature: Optional[str] = None
        self._similar_count = 0

    def analyze(
        self,
        tool_history: List[str],
        results: List[Dict],
    ) -> bool:
        """
        Returns True if converged (should stop).
        """
        signature = self._build_signature(tool_history, results)

        if signature == self._previous_signature:
            self._similar_count += 1
            logger.info(f"CONVERGENCE: count={self._similar_count}/{self.threshold}")
            if self._similar_count >= self.threshold:
                return True
        else:
            self._similar_count = 0

        self._previous_signature = signature
        return False

    def _build_signature(
        self,
        tool_history: List[str],
        results: List[Dict],
    ) -> str:
        normalized = [
            str(r).lower()[:200]
            for r in results
        ]
        return json.dumps({
            "tools": tool_history[-3:],
            "results": normalized
        }, sort_keys=True)

    def reset(self):
        """Reset convergence state."""
        self._previous_signature = None
        self._similar_count = 0


# ============================================================
# 4. METRICS COLLECTOR (Observability)
# ============================================================

class MetricsCollector:
    """
    Async metrics collection.
    Logs outside the critical path.
    """

    def __init__(self):
        self._logs: List[Dict] = []
        self._events: List[Dict] = []

    async def log_iteration(
        self,
        iteration: int,
        tool_calls: int,
        content_len: int,
    ):
        """Non-blocking metric logging."""
        entry = {
            "type": "iteration",
            "iteration": iteration,
            "tool_calls": tool_calls,
            "content_len": content_len,
        }
        self._events.append(entry)
        logger.info(f"METRIC: {entry}")

    async def log_tool_execution(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
    ):
        """Log tool execution metrics."""
        entry = {
            "type": "tool_execution",
            "tool_name": tool_name,
            "success": success,
            "duration_ms": duration_ms,
        }
        self._events.append(entry)
        logger.info(f"METRIC: {entry}")

    async def log_agent_start(
        self,
        chat_id: str,
        context_len: int,
        tools_count: int,
    ):
        """Log agent start."""
        entry = {
            "type": "agent_start",
            "chat_id": chat_id,
            "context_len": context_len,
            "tools_count": tools_count,
        }
        self._events.append(entry)
        logger.info(f"METRIC: {entry}")

    async def log_agent_stop(
        self,
        chat_id: str,
        iterations: int,
        reason: str,
    ):
        """Log agent stop."""
        entry = {
            "type": "agent_stop",
            "chat_id": chat_id,
            "iterations": iterations,
            "reason": reason,
        }
        self._events.append(entry)
        logger.info(f"METRIC: {entry}")

    def get_events(self) -> List[Dict]:
        return self._events.copy()

    def clear(self):
        """Clear all events."""
        self._events.clear()