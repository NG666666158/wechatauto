from __future__ import annotations

from typing import Iterable


def build_context_window(contexts: Iterable[str], limit: int = 10) -> list[str]:
    cleaned = [str(item).strip() for item in contexts if str(item).strip()]
    if limit <= 0:
        return cleaned
    return cleaned[-limit:]


def render_context_block(contexts: Iterable[str], limit: int = 10) -> str:
    window = build_context_window(contexts, limit=limit)
    if not window:
        return "(无上下文)"
    return "\n".join(f"{index + 1}. {message}" for index, message in enumerate(window))
