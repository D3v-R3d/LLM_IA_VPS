"""
Independent tool execution layer.
Handles timeouts, parallel/sequential categorization.
No knowledge of agent state, notifications, or budgets.
"""

import asyncio
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


TOOL_METADATA = {
    "api_fetch": {"parallelizable": True, "dangerous": False},
    "bash": {"parallelizable": False, "dangerous": True},
    "docker": {"parallelizable": False, "dangerous": True},
    "edit_file": {"parallelizable": False, "dangerous": True},
    "git": {"parallelizable": False, "dangerous": True},
    "glob": {"parallelizable": True, "dangerous": False},
    "grep": {"parallelizable": True, "dangerous": False},
    "ls": {"parallelizable": True, "dangerous": False},
    "pkill": {"parallelizable": False, "dangerous": True},
    "postgres_describe_table": {"parallelizable": True, "dangerous": False},
    "postgres_list_tables": {"parallelizable": True, "dangerous": False},
    "postgres_query": {"parallelizable": False, "dangerous": True},
    "read_file": {"parallelizable": True, "dangerous": False},
    "scrape_and_store": {"parallelizable": True, "dangerous": False},
    "search_stored_content": {"parallelizable": True, "dangerous": False},
    "telegram_bot_health": {"parallelizable": True, "dangerous": False},
    "telegram_get_user_info": {"parallelizable": True, "dangerous": False},
    "telegram_send_message": {"parallelizable": True, "dangerous": False},
    "telegram_send_notification": {"parallelizable": True, "dangerous": False},
    "user_write_notes": {"parallelizable": False, "dangerous": True},
    "web_fetch": {"parallelizable": True, "dangerous": False},
    "web_search": {"parallelizable": True, "dangerous": False},
    "write_file": {"parallelizable": False, "dangerous": True},
}


class ToolExecutor:
    """
    Independent tool executor.
    - No knowledge of agent state
    - No notifications
    - No budgets
    - Strict timeout only
    """

    def __init__(
        self,
        tools_service,
        registry,
        default_timeout: int = 30,
        max_tools_per_batch: int = 6,
    ):
        self.tools_service = tools_service
        self.registry = registry
        self.default_timeout = default_timeout
        self.max_tools_per_batch = max_tools_per_batch

    async def execute_batch(
        self,
        tool_calls: List[Dict],
    ) -> List[Dict]:
        """
        Execute a batch of tool calls.
        Returns list of results in same order as tool_calls.
        """
        if not tool_calls:
            return []

        # Limit number of tools
        tool_calls = tool_calls[:self.max_tools_per_batch]

        # Separate parallel vs sequential
        parallel, sequential = self._categorize(tool_calls)

        # Execute parallel tools first
        results = []
        if parallel:
            parallel_results = await asyncio.gather(*[
                self._execute_single(tc)
                for tc in parallel
            ], return_exceptions=True)
            # Convert exceptions to error dicts
            for r in parallel_results:
                if isinstance(r, Exception):
                    results.append({"success": False, "error": str(r)})
                else:
                    results.append(r)
        else:
            parallel_results = []

        # Execute sequential tools
        if sequential:
            for tc in sequential:
                result = await self._execute_single(tc)
                results.append(result)

        return results

    def _categorize(
        self,
        tool_calls: List[Dict]
    ) -> tuple[List[Dict], List[Dict]]:
        parallel, sequential = [], []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name")
            meta = TOOL_METADATA.get(name, {})
            if meta.get("parallelizable", True):
                parallel.append(tc)
            else:
                sequential.append(tc)
        return parallel, sequential

    async def _execute_single(
        self,
        tool_call: Dict,
        timeout: int = None,
    ) -> Dict:
        timeout = timeout or self.default_timeout
        func = tool_call.get("function", {})
        tool_name = func.get("name")
        arguments = func.get("arguments", {})

        try:
            result = await asyncio.wait_for(
                self._execute(tool_name, arguments),
                timeout=timeout + 5
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"TOOL_TIMEOUT: {tool_name} ({timeout}s)")
            return {"success": False, "error": f"Timeout after {timeout}s"}

        except Exception as e:
            logger.exception(f"TOOL_ERROR: {tool_name}")
            return {"success": False, "error": str(e)}

    async def _execute(self, tool_name: str, arguments: Dict) -> Dict:
        import json
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        try:
            result = await self.tools_service.execute_tool(tool_name, arguments)
        except Exception:
            result = {"error": "Unknown tool"}

        if isinstance(result, dict) and "Unknown tool" in str(result.get("error", "")):
            try:
                registry_result = await self.registry.execute(tool_name, **arguments)
                result = {
                    "success": registry_result.success,
                    "data": registry_result.data,
                    "error": registry_result.error
                }
            except Exception as e:
                result = {"success": False, "error": str(e)}

        return result