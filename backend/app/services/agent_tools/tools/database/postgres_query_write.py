"""
PostgreSQL Query Write Tool

Execute write PostgreSQL queries (INSERT/UPDATE/DELETE only).
Security: blocks DROP, ALTER, TRUNCATE, SELECT, etc.
"""

import re
from typing import Set

import psycopg2

from app.services.agent_tools.base.sync_tool import SyncTool, ToolResult
from app.core.config import settings

FORBIDDEN_WRITE: Set[str] = {
    "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    "EXECUTE", "DO", "CALL", "SELECT", "WITH"
}

WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}
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


class PostgresQueryWriteTool(SyncTool):
    """Execute write PostgreSQL queries (INSERT/UPDATE/DELETE only)."""

    META = {"category": "database", "max_calls_per_run": 3, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "postgres_query_write"

    @property
    def description(self) -> str:
        return "Execute a write PostgreSQL query (INSERT, UPDATE, or DELETE). IMPORTANT: First use postgres_describe_table to get table structure (column names). Returns affected row count."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "INSERT, UPDATE, or DELETE query"},
            },
            "required": ["query"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").strip()

        error = validate_query_type(query, WRITE_KEYWORDS, FORBIDDEN_WRITE)
        if error:
            return ToolResult(success=False, error=f"Write query rejected: {error}")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()
            cur.execute(f"SET statement_timeout = '{QUERY_TIMEOUT}s'")
            cur.execute(query)
            conn.commit()

            result = {"affected_rows": cur.rowcount, "status": "success"}
            cur.close()
            conn.close()
            return ToolResult(success=True, data=result)

        except psycopg2.errors.QueryCanceled:
            conn.rollback()
            return ToolResult(success=False, error=f"Query timeout ({QUERY_TIMEOUT}s exceeded)")
        except psycopg2.errors.InFailedSqlTransaction:
            conn.rollback()
            return ToolResult(success=False, error="Transaction error - query rolled back")
        except psycopg2.errors.InsufficientPrivilege:
            return ToolResult(success=False, error="Insufficient privileges to execute this query")
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg or "column" in error_msg.lower():
                return ToolResult(success=False, error=f"{error_msg}. Hint: Use postgres_describe_table to check table structure first.")
            return ToolResult(success=False, error=error_msg)