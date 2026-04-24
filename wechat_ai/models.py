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
    resolved_user_id: str | None = None
    conversation_id: str | None = None
    participant_display_name: str | None = None
    relationship_to_me: str | None = None
    current_intent: str | None = None
    identity_confidence: float | None = None
    identity_status: str | None = None
    identity_evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)
