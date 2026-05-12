"""
PostgreSQL List Tables Tool

List all tables in the database (read-only metadata).
Security: Uses information_schema only, excludes pg_catalog.
"""

import psycopg2

from app.services.agent_tools.base.sync_tool import SyncTool, ToolResult
from app.core.config import settings


class PostgresListTablesTool(SyncTool):
    """List all tables in the database (read-only metadata)."""

    META = {"category": "database", "max_calls_per_run": 10, "parallel_safe": True}

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