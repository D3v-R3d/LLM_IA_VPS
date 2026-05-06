"""
Database Tools - PostgreSQL queries

Tools for database operations.
"""

import psycopg2
from typing import Optional, Dict, Any

from app.services.agent_tools.tools.base_tool import BaseTool, ToolResult, SyncTool
from app.core.config import settings


class PostgresQueryTool(SyncTool):
    """Execute a PostgreSQL query."""

    @property
    def name(self) -> str:
        return "postgres_query"

    @property
    def description(self) -> str:
        return "Execute a PostgreSQL query. Returns results as list of dicts."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query to execute"},
                "params": {"type": "array", "description": "Query parameters"}
            },
            "required": ["query"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        params = kwargs.get("params")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()
            cur.execute(query, params)
            
            if query.strip().upper().startswith(("SELECT", "WITH")):
                columns = [desc[0] for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                result = {"columns": columns, "rows": rows, "count": len(rows)}
            else:
                conn.commit()
                result = {"affected_rows": cur.rowcount}

            cur.close()
            conn.close()
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PostgresListTablesTool(SyncTool):
    """List all tables in the database."""

    @property
    def name(self) -> str:
        return "postgres_list_tables"

    @property
    def description(self) -> str:
        return "List all tables in the PostgreSQL database."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    def _execute_sync(self, **kwargs) -> ToolResult:
        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            tables = [{"schema": row[0], "name": row[1]} for row in cur.fetchall()]
            cur.close()
            conn.close()
            return ToolResult(success=True, data={"tables": tables, "count": len(tables)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PostgresDescribeTableTool(SyncTool):
    """Describe a table structure."""

    @property
    def name(self) -> str:
        return "postgres_describe_table"

    @property
    def description(self) -> str:
        return "Get the structure of a PostgreSQL table."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table name to describe"}
            },
            "required": ["table"]
        }

    def _execute_sync(self, **kwargs) -> ToolResult:
        table = kwargs.get("table")
        
        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = [{"name": row[0], "type": row[1], "nullable": row[2], "default": row[3]} for row in cur.fetchall()]
            cur.close()
            conn.close()
            return ToolResult(success=True, data={"table": table, "columns": columns})
        except Exception as e:
            return ToolResult(success=False, error=str(e))