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

from app.services.agent_core.tool_response import ToolResponse
from app.services.agent_core.tool_metadata import ToolMetadata
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
    "postgres_query_read": {"parallelizable": False, "dangerous": False},
    "postgres_query_write": {"parallelizable": False, "dangerous": True},
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
        self._summarizer.validate_handlers(registry)

    async def execute_batch(
        self,
        tool_calls: List[Dict],
        user_id: Optional[str] = None,
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
                self._execute_single(tc, user_id=user_id)
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
                results.append(await self._execute_single(tc, user_id=user_id))

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
        user_id: Optional[str] = None,
    ) -> ToolResponse:
        timeout = timeout or self.default_timeout
        func = tool_call.get("function", {})
        tool_name = func.get("name", "unknown")
        arguments = func.get("arguments", {})
        start = time.perf_counter()
        
        # Check permissions before execution
        from app.services.agent_tools.utils.permissions import get_permissions
        perms = get_permissions()
        
        if not perms.is_allowed(tool_name, user=user_id):
            duration = (time.perf_counter() - start) * 1000
            logger.warning(f"PERMISSION_DENIED: {tool_name} for user {user_id}")
            return ToolResponse(
                success=False,
                tool=tool_name,
                summary=f"Permission denied: {tool_name}",
                error=f"Tool {tool_name} is not allowed",
                metadata=ToolMetadata(duration_ms=duration)
            )
        
# Check if confirmation is required
        if perms.requires_confirmation(tool_name):
            confirmation_msg = perms.get_confirmation_message(tool_name, arguments)
            logger.info(f"CONFIRMATION_REQUIRED: {tool_name} - {confirmation_msg}")
        
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
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                # If arguments is a string but not valid JSON, treat it as empty dict
                # This can happen when LLM returns malformed JSON
                logger.warning(f"Failed to parse tool arguments as JSON for {tool_name}: {arguments}")
                arguments = {}
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


# ═══════════════════════════════════════════════════════════════════════
# RESULT MERGER - Deterministic merging for ambiguous queries
# ═══════════════════════════════════════════════════════════════════════

# Scope priority: local_fs > nas > vector > postgres > web > others
SCOPE_PRIORITY = ["local_fs", "nas", "vector", "postgres", "web", "telegram", "docker", "system", "memory", "api", "database"]

# Tool → Scope mapping (same as tool_router.py)
TOOL_TO_SCOPE = {
    "glob": "local_fs", "ls": "local_fs", "find": "local_fs", "read_file": "local_fs", "grep": "local_fs",
    "write_file": "local_fs", "edit_file": "local_fs",
    "nas_find_folder": "nas", "nas_find_file": "nas", "nas_search": "nas", "nas_list_folder": "nas", "nas_list_share": "nas",
    "qdrant_search": "vector", "search_stored_content": "vector", "scrape_and_store": "vector",
    "postgres_query_read": "postgres", "postgres_query_write": "postgres", "postgres_list_tables": "postgres", "postgres_describe_table": "postgres",
    "telegram_send_message": "telegram", "telegram_send_notification": "telegram", "telegram_get_user_info": "telegram", "telegram_bot_health": "telegram",
    "web_search": "web", "web_fetch": "web", "api_call": "web",
    "docker": "docker",
    "bash": "system", "pkill": "system", "git": "system",
    "user_write_notes": "memory",
}


def get_tool_scope(tool_name: str) -> Optional[str]:
    """Get the scope for a given tool name."""
    return TOOL_TO_SCOPE.get(tool_name)


class ResultMerger:
    """
    Deterministic result merging for ambiguous queries.
    
    Priority: local_fs > nas > vector (weighted, not strict)
    - If local_fs has success results → return local_fs
    - Elif nas has success results → return nas
    - Else → return vector
    """
    
    @staticmethod
    def merge_results(
        tool_results: List[ToolResponse],
        router_metadata: Optional[Dict] = None
    ) -> List[ToolResponse]:
        """
        Merge results with scope-based priority.
        
        Rules:
        1. Group by scope
        2. Return highest-priority non-empty scope
        3. Include all results from that scope
        
        Args:
            tool_results: List of tool execution results
            router_metadata: Router result dict with scope_candidates
        
        Returns:
            Filtered list of results from highest-priority scope with results
        """
        if not tool_results:
            return []
        
        # Group results by scope
        from collections import defaultdict
        scope_results = defaultdict(list)
        
        for result in tool_results:
            if result.success:
                scope = get_tool_scope(result.tool)
                if scope:
                    scope_results[scope].append(result)
        
        # If not ambiguous, return all results as-is
        if not router_metadata or not router_metadata.get("is_ambiguous"):
            return tool_results
        
        # Return highest-priority non-empty scope
        for scope in SCOPE_PRIORITY:
            if scope_results.get(scope):
                logger.info(f"ResultMerger: selected scope '{scope}' ({len(scope_results[scope])} results)")
                return scope_results[scope]
        
        # All scopes empty → return all results (let LLM explain)
        logger.info(f"ResultMerger: all scopes empty, returning all {len(tool_results)} results")
        return tool_results