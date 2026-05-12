"""
PostgreSQL Query Read Tool

Execute read-only PostgreSQL queries (SELECT/WITH only).
Security: blocks INSERT, UPDATE, DELETE, DROP, etc.
"""

import re
import psycopg2
from typing import Set

from app.services.agent_tools.base.sync_tool import SyncTool, ToolResult
from app.core.config import settings

FORBIDDEN_READ: Set[str] = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXECUTE", "DO", "CALL"
}

READ_ONLY_KEYWORDS = {"SELECT", "WITH"}
QUERY_TIMEOUT = 30


def validate_query_type(query: str, allowed_keywords: Set[str], forbidden_keywords: Set[str]):
    if not query:
        return "Empty query"
    query_upper = query.upper()
    for keyword in forbidden_keywords:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_upper):
            return f"Forbidden keyword: {keyword}"
    if allowed_keywords:
        has_allowed = any(re.search(r'\b' + kw + r'\b', query_upper) for kw in allowed_keywords)
        if not has_allowed:
            return f"Query must start with: {', '.join(allowed_keywords)}"
    return None


def add_limit_if_needed(query: str, default_limit: int = 1000) -> str:
    query_upper = query.strip().upper()
    if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
        return f"{query.strip().rstrip(';')} LIMIT {default_limit}"
    return query


class PostgresQueryReadTool(SyncTool):
    """Execute read-only PostgreSQL queries (SELECT/WITH only)."""

    META = {"category": "database", "max_calls_per_run": 10, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "postgres_query_read"

    @property
    def description(self) -> str:
        return "Execute a read-only PostgreSQL query (SELECT or WITH). Returns structured results. LIMIT 1000 applied automatically."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SELECT or WITH query to execute"},
            },
            "required": ["query"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").strip()

        error = validate_query_type(query, READ_ONLY_KEYWORDS, FORBIDDEN_READ)
        if error:
            return ToolResult(success=False, error=f"Read query rejected: {error}")

        query = add_limit_if_needed(query, 1000)

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"SET statement_timeout = '{QUERY_TIMEOUT}s'")
            cur.execute(query)

            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                result = {"columns": columns, "rows": rows, "count": len(rows)}
            else:
                result = {"message": "Query executed successfully, no rows returned"}

            cur.close()
            conn.close()
            return ToolResult(success=True, data=result)

        except psycopg2.errors.QueryCanceled:
            return ToolResult(success=False, error=f"Query timeout ({QUERY_TIMEOUT}s exceeded)")
        except psycopg2.errors.InFailedSqlTransaction:
            return ToolResult(success=False, error="Transaction error - query rolled back")
        except Exception as e:
            return ToolResult(success=False, error=str(e))