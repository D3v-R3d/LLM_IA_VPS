"""
PostgreSQL Describe Table Tool

Describe a table structure (read-only metadata).
Security: Uses information_schema only.
"""

import re

import psycopg2

from app.services.agent_tools.base.sync_tool import SyncTool, ToolResult
from app.core.config import settings


class PostgresDescribeTableTool(SyncTool):
    """Describe a table structure (read-only metadata)."""

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