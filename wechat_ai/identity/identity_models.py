from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class IdentityRawSignal:
    conversation_id: str
    chat_type: str
    display_name: str
    text: str
    contexts: list[str] = field(default_factory=list)
    group_name: str | None = None
    sender_name: str | None = None
    captured_at: str | None = None


@dataclass(slots=True)
class UserIdentity:
    user_id: str
    canonical_name: str
    user_type: str = "未知"
    relationship_to_me: str = "未知"
    status: str = "confirmed"
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class UserAlias:
    user_id: str
    display_names: list[str] = field(default_factory=list)
    remarks: list[str] = field(default_factory=list)
    group_nicknames: list[dict[str, str]] = field(default_factory=list)
    latest_seen_name: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class DraftUser:
    draft_user_id: str
    proposed_name: str
    proposed_user_type: str = "未知"
    current_intent: str = "未知"
    relationship_to_me: str = "未知"
    confidence: float = 0.3
    source_signals: list[str] = field(default_factory=list)
    status: str = "draft"
    conversation_id: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class IdentityCandidate:
    candidate_id: str
    incoming_name: str
    matched_user_id: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    conversation_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "pending_review"


@dataclass(slots=True)
class IdentityResolutionResult:
    resolved_user_id: str | None = None
    draft_user_id: str | None = None
    candidate_id: str | None = None
    conversation_id: str | None = None
    participant_display_name: str | None = None
    relationship_to_me: str | None = None
    current_intent: str | None = None
    identity_confidence: float | None = None
    identity_status: str = "unknown"
    evidence: list[str] = field(default_factory=list)
