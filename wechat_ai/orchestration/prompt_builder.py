from __future__ import annotations

from collections.abc import Iterable, Mapping

from wechat_ai.context import render_context_block


class PromptBuilder:
    def __init__(self, context_limit: int = 10) -> None:
        self.context_limit = context_limit

    def render_prompt(
        self,
        *,
        scene: str,
        latest_message: str,
        contexts: list[str],
        agent_profile: object | None = None,
        user_profile: object | None = None,
        knowledge_chunks: list[str] | None = None,
        memory_summary: str | None = None,
    ) -> str:
        sections = [
            self._render_agent_profile_summary(agent_profile),
            self._render_user_profile_summary(user_profile),
            self._render_recent_conversation_context(contexts),
            self._render_retrieved_knowledge(knowledge_chunks or []),
            self._render_memory_summary(memory_summary),
            self._render_current_reply_task(scene=scene, latest_message=latest_message),
        ]
        return "\n\n".join(section for section in sections if section)

    def debug_preview(self, **kwargs: object) -> str:
        return self.render_prompt(**kwargs)

    def _render_agent_profile_summary(self, profile: object | None) -> str:
        lines = ["## Agent Profile Summary"]
        if profile is None:
            lines.append("(no agent profile)")
            return "\n".join(lines)

        lines.extend(
            [
                f"Name: {self._first_text(getattr(profile, 'display_name', ''), getattr(profile, 'agent_id', 'unknown'))}",
                self._render_list_line("Style rules", getattr(profile, "style_rules", [])),
                self._render_list_line("Goals", getattr(profile, "goals", [])),
                self._render_list_line("Forbidden rules", getattr(profile, "forbidden_rules", [])),
                self._render_list_line("Notes", getattr(profile, "notes", [])),
            ]
        )
        return "\n".join(lines)

    def _render_user_profile_summary(self, profile: object | None) -> str:
        lines = ["## User Profile Summary"]
        if profile is None:
            lines.append("(no user profile)")
            return "\n".join(lines)

        lines.extend(
            [
                f"Name: {self._first_text(getattr(profile, 'display_name', ''), getattr(profile, 'user_id', 'unknown'))}",
                self._render_list_line("Tags", getattr(profile, "tags", [])),
                self._render_list_line("Notes", getattr(profile, "notes", [])),
                self._render_preferences_line(getattr(profile, "preferences", {})),
            ]
        )
        return "\n".join(lines)

    def _render_recent_conversation_context(self, contexts: list[str]) -> str:
        return "## Recent Conversation Context\n" + render_context_block(contexts, limit=self.context_limit)

    def _render_retrieved_knowledge(self, knowledge_chunks: list[str]) -> str:
        lines = ["## Retrieved Knowledge"]
        cleaned = [str(chunk).strip() for chunk in knowledge_chunks if str(chunk).strip()]
        if not cleaned:
            lines.append("(no retrieved knowledge)")
            return "\n".join(lines)
        lines.extend(f"{index + 1}. {chunk}" for index, chunk in enumerate(cleaned))
        return "\n".join(lines)

    def _render_current_reply_task(self, *, scene: str, latest_message: str) -> str:
        return (
            "## Current Reply Task\n"
            f"Scene: {scene}\n"
            f"Latest message: {latest_message}\n"
            "Write a direct Chinese WeChat reply with no extra explanation."
        )

    def _render_memory_summary(self, memory_summary: str | None) -> str:
        cleaned = str(memory_summary or "").strip()
        if not cleaned:
            return ""
        return "## Conversation Memory Summary\n" + cleaned

    def _render_list_line(self, label: str, values: Iterable[object]) -> str:
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        return f"{label}: {', '.join(cleaned) if cleaned else '(none)'}"

    def _render_preferences_line(self, preferences: object) -> str:
        if isinstance(preferences, Mapping):
            pairs = [f"{key}={value}" for key, value in preferences.items() if str(value).strip()]
            return f"Preferences: {', '.join(pairs) if pairs else '(none)'}"
        return "Preferences: (none)"

    def _first_text(self, *values: object) -> str:
        for value in values:
            text = str(value).strip()
            if text:
                return text
        return "unknown"
