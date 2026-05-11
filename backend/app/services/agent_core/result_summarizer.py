"""
Result Summarizer

Generates LLM-friendly summaries from tool responses.
Specialized per tool type for concise, relevant output.
"""

import re
import logging
from typing import Any, Dict, Optional
from app.services.agent_core.tool_response import ToolResponse

logger = logging.getLogger(__name__)


class ResultSummarizer:
    """Generate LLM-friendly summaries from tool results."""

    MAX_SUMMARY_CHARS = 5000
    MAX_LIST_ITEMS = 25

    HANDLERS = {
        "read_file": "_file_summary",
        "write_file": "_write_summary",
        "edit_file": "_edit_summary",
        "glob": "_glob_summary",
        "grep": "_grep_summary",
        "ls": "_list_summary",

        "web_search": "_search_summary",
        "web_fetch": "_web_fetch_summary",
        "api_fetch": "_web_fetch_summary",

        "bash": "_bash_summary",
        "docker": "_docker_summary",
        "git": "_git_summary",
        "pkill": "_bash_summary",

        "postgres_query_read": "_query_summary",
        "postgres_query_write": "_query_summary",
        "postgres_list_tables": "_list_summary",
        "postgres_describe_table": "_describe_summary",

        "telegram_send_message": "_default_summary",
        "telegram_send_notification": "_default_summary",
        "telegram_get_user_info": "_default_summary",
        "telegram_bot_health": "_default_summary",

        "user_write_notes": "_default_summary",

        "scrape_and_store": "_default_summary",
        "search_stored_content": "_search_summary",

        "qdrant_search": "_search_summary",

        "nas_list_share": "_list_summary",
        "nas_list_folder": "_list_summary",
        "nas_search": "_search_summary",

        "model_switch": "_default_summary",
    }

    def summarize(self, tool_name: str, response: ToolResponse) -> str:
        if not response.success:
            return self._error_summary(response)

        handler_name = self.HANDLERS.get(tool_name, "_default_summary")
        handler = getattr(self, handler_name)
        return handler(response)

    def _error_summary(self, response: ToolResponse) -> str:
        return f"Error ({response.tool}): {response.error or 'Unknown error'}"

    def _default_summary(self, response: ToolResponse) -> str:
        text = str(response.data) if response.data else ""
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > self.MAX_SUMMARY_CHARS:
            text = text[:self.MAX_SUMMARY_CHARS] + "... [truncated]"
        return text

    def _search_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        results = data.get("results") if isinstance(data, dict) else data
        if isinstance(results, list):
            lines = [f"Found {len(results)} results:"]
            for r in results[:self.MAX_LIST_ITEMS]:
                if isinstance(r, dict):
                    title = r.get("title", r.get("name", "Untitled"))
                    snippet = str(r.get("snippet", r.get("content", "")))[:200]
                    lines.append(f"- {title}: {snippet}")
                else:
                    lines.append(f"- {str(r)[:200]}")
            if len(results) > self.MAX_LIST_ITEMS:
                lines.append(f"... and {len(results) - self.MAX_LIST_ITEMS} more")
            return "\n".join(lines)
        return self._default_summary(response)

    def _web_fetch_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        content = ""
        if isinstance(data, dict):
            content = data.get("content") or data.get("text") or str(data)
        else:
            content = str(data)
        content = re.sub(r"\s+", " ", content).strip()
        if len(content) > self.MAX_SUMMARY_CHARS:
            content = content[:self.MAX_SUMMARY_CHARS] + "... [truncated]"
        return content

    def _file_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        content = data.get("content", "") if isinstance(data, dict) else str(data)
        total = data.get("total_lines", 0) if isinstance(data, dict) else 0
        offset = data.get("offset", 1) if isinstance(data, dict) else 1
        header = f"File (lines {offset}-{offset + content.count(chr(10))}, total {total}):\n"
        return header + content[:self.MAX_SUMMARY_CHARS]

    def _write_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        path = data.get("file_path", "unknown") if isinstance(data, dict) else "unknown"
        size = data.get("bytes_written", 0) if isinstance(data, dict) else 0
        return f"Written {size} bytes to {path}"

    def _edit_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        path = data.get("file_path", "unknown") if isinstance(data, dict) else "unknown"
        count = data.get("replacements", 1) if isinstance(data, dict) else 1
        return f"Edited {path} ({count} replacement(s))"

    def _glob_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        matches = data.get("matches", []) if isinstance(data, dict) else []
        count = data.get("count", len(matches)) if isinstance(data, dict) else len(matches)
        lines = [f"Found {count} files:"]
        for m in matches[:self.MAX_LIST_ITEMS]:
            lines.append(f"- {m}")
        if count > self.MAX_LIST_ITEMS:
            lines.append(f"... and {count - self.MAX_LIST_ITEMS} more")
        return "\n".join(lines)

    def _grep_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        results = data.get("results", []) if isinstance(data, dict) else []
        count = data.get("count", len(results)) if isinstance(data, dict) else len(results)
        lines = [f"Found {count} matches:"]
        for r in results[:self.MAX_LIST_ITEMS]:
            if isinstance(r, dict):
                file = r.get("file", "?")
                line = r.get("line", "?")
                content = str(r.get("content", ""))[:100]
                lines.append(f"{file}:{line}: {content}")
            else:
                lines.append(str(r))
        if count > self.MAX_LIST_ITEMS:
            lines.append(f"... and {count - self.MAX_LIST_ITEMS} more")
        return "\n".join(lines)

    def _list_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        entries = []
        if isinstance(data, dict):
            entries = (data.get("entries") or data.get("tables") or
                       data.get("points") or [])
        items = []
        for e in entries[:self.MAX_LIST_ITEMS]:
            if isinstance(e, dict):
                name = e.get("name", e.get("table", str(e.get("id", "?"))))
                kind = e.get("type", "")
                size = e.get("size", "")
                items.append(f"  {'📁' if kind == 'dir' else '📄'} {name}" +
                             (f" ({size}B)" if size else ""))
            else:
                items.append(f"  - {e}")
        total = data.get("count", data.get("total", len(entries))) if isinstance(data, dict) else len(entries)
        header = f"Found {total} items:\n" if total else ""
        return header + "\n".join(items)

    def _bash_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)
        stderr = data.get("stderr", "") if isinstance(data, dict) else ""
        parts = []
        if stdout:
            trimmed = stdout.strip()
            if len(trimmed) > self.MAX_SUMMARY_CHARS:
                trimmed = trimmed[:self.MAX_SUMMARY_CHARS] + "... [truncated]"
            parts.append(trimmed)
        if stderr:
            parts.append(f"stderr: {stderr.strip()[:500]}")
        return "\n".join(parts) if parts else "(no output)"

    def _docker_summary(self, response: ToolResponse) -> str:
        return self._default_summary(response)

    def _git_summary(self, response: ToolResponse) -> str:
        return self._bash_summary(response)

    def validate_handlers(self, registry):
        missing = [
            t.name for t in registry.get_all()
            if t.name not in self.HANDLERS
        ]
        if missing:
            logger.warning(f"Missing summarizers: {missing}")

    def _query_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        if isinstance(data, dict):
            if "rows" in data:
                rows = data["rows"]
                cols = data.get("columns", [])
                count = data.get("count", len(rows))
                lines = [f"Query returned {count} rows:"]
                for row in rows[:self.MAX_LIST_ITEMS]:
                    if isinstance(row, dict):
                        items = [f"{c}={row.get(c, '')}" for c in cols[:5]]
                        lines.append(f"  {', '.join(items)}")
                    else:
                        lines.append(f"  {row}")
                if count > self.MAX_LIST_ITEMS:
                    lines.append(f"  ... and {count - self.MAX_LIST_ITEMS} more")
                return "\n".join(lines)
            elif "affected_rows" in data:
                return f"Query OK, {data['affected_rows']} rows affected"
        return self._default_summary(response)

    def _describe_summary(self, response: ToolResponse) -> str:
        data = response.data or {}
        table = data.get("table", "?") if isinstance(data, dict) else "?"
        columns = data.get("columns", []) if isinstance(data, dict) else []
        lines = [f"Table: {table} ({len(columns)} columns)"]
        for col in columns[:10]:
            if isinstance(col, dict):
                lines.append(f"  {col.get('name', '?')}: {col.get('type', '?')}")
        return "\n".join(lines)
