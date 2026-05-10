"""
Independent tool execution layer.
Handles timeouts, parallel/sequential categorization, standardized outputs.
No knowledge of agent state, notifications, or budgets.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.agent_core.tool_response import ToolResponse, ToolMetadata
from app.services.agent_tools.base.base_tool import ToolResult
from app.services.agent_core.result_summarizer import ResultSummarizer

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
    Independent tool executor with standardized outputs.
    - No knowledge of agent state
    - No notifications
    - No budgets
    - Strict timeout only
    - Returns ToolResponse objects
    """

    def __init__(
        self,
        registry,
        default_timeout: int = 30,
        max_tools_per_batch: int = 6,
    ):
        self.registry = registry
        self.default_timeout = default_timeout
        self.max_tools_per_batch = max_tools_per_batch
        self._summarizer = ResultSummarizer()

    async def execute_batch(
        self,
        tool_calls: List[Dict],
    ) -> List[ToolResponse]:
        """
        Execute a batch of tool calls.
        Returns list of ToolResponse in same order as tool_calls.
        """
        if not tool_calls:
            return []

        # Limit number of tools
        tool_calls = tool_calls[:self.max_tools_per_batch]

        # Separate parallel vs sequential
        parallel, sequential = self._categorize(tool_calls)

        # Execute parallel tools first
        results: List[ToolResponse] = []
        if parallel:
            parallel_results = await asyncio.gather(*[
                self._execute_single(tc)
                for tc in parallel
            ], return_exceptions=True)
            for r in parallel_results:
                if isinstance(r, Exception):
                    results.append(ToolResponse(
                        success=False,
                        tool="unknown",
                        summary=f"Exception: {r}",
                        error=str(r)
                    ))
                else:
                    results.append(r)
        else:
            parallel_results = []

        # Execute sequential tools
        if sequential:
            for tc in sequential:
                results.append(await self._execute_single(tc))

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
    ) -> ToolResponse:
        timeout = timeout or self.default_timeout
        func = tool_call.get("function", {})
        tool_name = func.get("name", "unknown")
        arguments = func.get("arguments", {})
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self._execute(tool_name, arguments),
                timeout=timeout + 5
            )
            duration = (time.perf_counter() - start) * 1000
            response = ToolResponse(
                success=result.success,
                tool=tool_name,
                summary=self._summarizer.summarize(tool_name, ToolResponse(
                    success=result.success,
                    tool=tool_name,
                    summary="",
                    data=result.data,
                    error=result.error,
                )),
                data=result.data,
                error=result.error,
                metadata=ToolMetadata(duration_ms=duration)
            )

        except asyncio.TimeoutError:
            duration = (time.perf_counter() - start) * 1000
            logger.error(f"TOOL_TIMEOUT: {tool_name} ({timeout}s)")
            response = ToolResponse(
                success=False,
                tool=tool_name,
                summary=f"Timeout after {timeout}s",
                error=f"Timeout after {timeout}s",
                metadata=ToolMetadata(duration_ms=duration)
            )

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            logger.exception(f"TOOL_ERROR: {tool_name}")
            response = ToolResponse(
                success=False,
                tool=tool_name,
                summary=f"Error: {str(e)[:200]}",
                error=str(e),
                metadata=ToolMetadata(duration_ms=duration)
            )

        logger.info(f"Tool {tool_name}: {response.to_log_dict()}")
        return response

    async def _execute(self, tool_name: str, arguments: Dict) -> ToolResult:
        import json
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        # Fix common LLM type errors: string numbers -> int
        fixed = {}
        for k, v in arguments.items():
            if isinstance(v, str) and v.lstrip('-').isdigit():
                fixed[k] = int(v)
            elif isinstance(v, str) and v.replace('.', '', 1).lstrip('-').isdigit():
                fixed[k] = float(v)
            else:
                fixed[k] = v
        return await self.registry.execute(tool_name, **fixed)