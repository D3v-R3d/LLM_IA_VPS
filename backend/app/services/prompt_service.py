import os
from typing import Optional
from app.core.config import settings

_prompt_cache: dict[str, str] = {}
_cache_loaded = False


class PromptService:

    @staticmethod
    def load_inject_files() -> dict[str, str]:
        global _prompt_cache, _cache_loaded
        if not _cache_loaded:
            inject_folder = os.path.join(settings.PROMPT_DIR, "inject")
            try:
                for filename in os.listdir(inject_folder):
                    if filename.endswith(".md"):
                        filepath = os.path.join(inject_folder, filename)
                        try:
                            with open(filepath, "r") as f:
                                content = f.read()
                            _prompt_cache[filename] = content
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                _cache_loaded = True
        return dict(_prompt_cache)

    @staticmethod
    def get_context_summary() -> str:
        try:
            summary_path = f"{settings.PROMPT_DIR}/inject/context_summary.md"
            with open(summary_path, "r") as f:
                parts = f.read().split("<!-- Summary will be injected here -->")
                if len(parts) > 1:
                    return parts[1].strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def get_notes() -> str:
        try:
            notes_path = f"{settings.PROMPT_DIR}/inject/notes.md"
            with open(notes_path, "r") as f:
                return f.read().strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def build_files_section(files_content: dict[str, str]) -> str:
        section = ""
        for filename, content in files_content.items():
            if filename in ("context_summary.md", "notes.md"):
                continue
            if content:
                section += f"\n\n=== {filename} ===\n{content[:8000]}"
        return section[:30000]

    @staticmethod
    def build_system_message(
        context_summary: str,
        notes_content: str,
        files_content: dict[str, str],
        user_preferences: Optional[dict] = None
    ) -> dict:
        files_section = PromptService.build_files_section(files_content)
        context_section = f"\n\n### Previous Conversation Summary:\n{context_summary}\n" if context_summary else ""
        notes_section = f"\n\n### User Notes:\n{notes_content}\n" if notes_content else ""

        pref_text = ""
        if user_preferences:
            pref_lines = [f"• {k}: {v}" for k, v in user_preferences.items() if k != "current_session"]
            if pref_lines:
                pref_text = "\nUser preferences:\n" + "\n".join(pref_lines)

        model_name = user_preferences.get("model") if user_preferences else None
        model_section = f"\n\n**Current Model:** `{model_name}`" if model_name else ""

        return {
            "role": "system",
            "content": f"""You are a helpful assistant.{context_section}{notes_section}{files_section}{model_section}
{pref_text}"""
        }

    @staticmethod
    def get_system_message(user_preferences: Optional[dict] = None) -> dict:
        files_content = PromptService.load_inject_files()
        context_summary = PromptService.get_context_summary()
        notes = PromptService.get_notes()
        return PromptService.build_system_message(
            context_summary=context_summary,
            notes_content=notes,
            files_content=files_content,
            user_preferences=user_preferences
        )

    @staticmethod
    def get_summarize_prompt() -> str:
        try:
            path = os.path.join(settings.PROMPT_DIR, "generate", "summarize.md")
            with open(path, "r") as f:
                return f.read()
        except Exception:
            return "Summarize the conversation briefly."

    @staticmethod
    def write_context_summary(summary: str):
        from datetime import datetime
        try:
            summary_path = os.path.join(settings.PROMPT_DIR, "inject", "context_summary.md")
            with open(summary_path, "r") as f:
                content = f.read()
            header = content.split("<!-- Summary will be injected here -->")[0]
            with open(summary_path, "w") as f:
                f.write(f"{header}<!-- Summary will be injected here -->\n[{datetime.utcnow().isoformat()}] {summary}")
        except Exception:
            pass
