"""
PostgreSQL database tools - Separated for security.

Tools:
- postgres_query_read: SELECT/WITH only (read-only)
- postgres_query_write: INSERT/UPDATE/DELETE only (write operations)
- postgres_list_tables: List all tables (metadata)
- postgres_describe_table: Describe table structure (metadata)
"""

import re
import psycopg2
from typing import Optional, Dict, Any, Set

from app.services.agent_tools.base.base_tool import BaseTool, ToolResult
from app.services.agent_tools.base.sync_tool import SyncTool
from app.core.config import settings

# Security: Forbidden keywords for each tool type
FORBIDDEN_READ: Set[str] = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXECUTE", "DO", "CALL"
}

FORBIDDEN_WRITE: Set[str] = {
    "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    "EXECUTE", "DO", "CALL", "SELECT", "WITH"
}

READ_ONLY_KEYWORDS = {"SELECT", "WITH"}
WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}

# Query timeout in seconds
QUERY_TIMEOUT = 30


def validate_query_type(query: str, allowed_keywords: Set[str], forbidden_keywords: Set[str]) -> Optional[str]:
    """
    Validate query against allowed/forbidden keywords.
    Returns error message if invalid, None if valid.
    """
    if not query:
        return "Empty query"

    query_upper = query.upper()

    # Check for forbidden keywords
    for keyword in forbidden_keywords:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_upper):
            return f"Forbidden keyword: {keyword}"

    # Check for required keywords
    if allowed_keywords:
        has_allowed = any(re.search(r'\b' + kw + r'\b', query_upper) for kw in allowed_keywords)
        if not has_allowed:
            return f"Query must start with: {', '.join(allowed_keywords)}"

    return None


def add_limit_if_needed(query: str, default_limit: int = 1000) -> str:
    """Add LIMIT if not present and query is SELECT."""
    query_upper = query.strip().upper()
    if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
        return f"{query.strip().rstrip(';')} LIMIT {default_limit}"
    return query


class PostgresQueryReadTool(SyncTool):
    """
    Execute read-only PostgreSQL queries (SELECT/WITH only).
    Security: blocks INSERT, UPDATE, DELETE, DROP, etc.
    """

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

        # Validate query type
        error = validate_query_type(query, READ_ONLY_KEYWORDS, FORBIDDEN_READ)
        if error:
            return ToolResult(success=False, error=f"Read query rejected: {error}")

        # Add LIMIT if not present
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
                result = {
                    "columns": columns,
                    "rows": rows,
                    "count": len(rows)
                }
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


class PostgresQueryWriteTool(SyncTool):
    """
    Execute write PostgreSQL queries (INSERT/UPDATE/DELETE only).
    Security: blocks DROP, ALTER, TRUNCATE, SELECT, etc.
    """

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

        # Validate query type
        error = validate_query_type(query, WRITE_KEYWORDS, FORBIDDEN_WRITE)
        if error:
            return ToolResult(success=False, error=f"Write query rejected: {error}")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)

            cur = conn.cursor()
            cur.execute(f"SET statement_timeout = '{QUERY_TIMEOUT}s'")

            cur.execute(query)
            conn.commit()

            result = {
                "affected_rows": cur.rowcount,
                "status": "success"
            }

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


class PostgresListTablesTool(SyncTool):
    """
    List all tables in the database (read-only metadata).
    Security: Uses information_schema only, excludes pg_catalog.
    """

    META = {"category": "database", "max_calls_per_run": 5, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "postgres_list_tables"

    @property
    def description(self) -> str:
        return "List all user tables in the PostgreSQL database using information_schema."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "schema": {"type": "string", "description": "Filter by schema name (optional)"}
            }
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        schema_filter = kwargs.get("schema")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            conn.autocommit = True

            cur = conn.cursor()

            if schema_filter:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    AND table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """, (schema_filter,))
            else:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """)

            tables = [{"schema": row[0], "name": row[1]} for row in cur.fetchall()]

            cur.close()
            conn.close()

            return ToolResult(success=True, data={"tables": tables, "count": len(tables)})

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PostgresDescribeTableTool(SyncTool):
    """
    Describe a table structure (read-only metadata).
    Security: Uses information_schema only.
    """

    META = {"category": "database", "max_calls_per_run": 10, "parallel_safe": True}

    @property
    def name(self) -> str:
        return "postgres_describe_table"

    @property
    def description(self) -> str:
        return "Get the structure of a PostgreSQL table (columns, types, defaults)."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table name to describe"},
                "schema": {"type": "string", "description": "Schema name (optional, defaults to 'public')"}
            },
            "required": ["table"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        table = kwargs.get("table", "").strip()
        schema = kwargs.get("schema", "public")

        if not table:
            return ToolResult(success=False, error="Missing table name")

        # Basic SQL injection protection - only allow valid identifier chars
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            return ToolResult(success=False, error="Invalid table name format")

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
            return ToolResult(success=False, error="Invalid schema name format")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            conn.autocommit = True

            cur = conn.cursor()
            cur.execute("""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale
                FROM information_schema.columns c
                WHERE c.table_name = %s
                AND c.table_schema = %s
                ORDER BY c.ordinal_position
            """, (table, schema))

            columns = []
            for row in cur.fetchall():
                col_info = {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3]
                }
                # Add length/precision if applicable
                if row[4]:
                    col_info["max_length"] = row[4]
                if row[5]:
                    col_info["precision"] = row[5]
                if row[6] is not None:
                    col_info["scale"] = row[6]

                columns.append(col_info)

            cur.close()
            conn.close()

            if not columns:
                return ToolResult(success=False, error=f"Table '{table}' not found in schema '{schema}'")

            return ToolResult(success=True, data={"table": table, "schema": schema, "columns": columns})

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Backwards compatibility - keep old tool but mark as deprecated
class PostgresQueryTool(SyncTool):
    """
    DEPRECATED: Use postgres_query_read or postgres_query_write instead.
    This tool exists for backwards compatibility only.
    """

    META = {"category": "database", "max_calls_per_run": 0, "parallel_safe": False}

    @property
    def name(self) -> str:
        return "postgres_query"

    @property
    def description(self) -> str:
        return "[DEPRECATED] Use postgres_query_read or postgres_query_write instead."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "[DEPRECATED] SQL query"},
                "mode": {"type": "string", "description": "read or write (required)"}
            },
            "required": ["query", "mode"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=False,
            error="postgres_query is deprecated. Use postgres_query_read (SELECT/WITH) or postgres_query_write (INSERT/UPDATE/DELETE) instead."
        )