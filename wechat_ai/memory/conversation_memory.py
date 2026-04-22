from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationSnapshot:
    messages: list[str]
    captured_at: str
