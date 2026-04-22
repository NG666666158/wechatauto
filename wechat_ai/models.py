from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Message:
    chat_id: str
    chat_type: str
    sender_name: str
    text: str
    timestamp: str | None = None
    context: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)
