from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GlobalSelfIdentityProfile:
    profile_id: str = "global"
    display_name: str = ""
    identity_facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    style_hints: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RelationshipSelfIdentityProfile:
    relationship: str
    display_name: str = ""
    trigger_tags: list[str] = field(default_factory=list)
    identity_facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    style_hints: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserSelfIdentityOverride:
    user_id: str
    relationship_override: str = ""
    display_name: str = ""
    identity_facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    style_hints: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResolvedSelfIdentityProfile:
    user_id: str = ""
    relationship: str = ""
    display_name: str = ""
    identity_facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    style_hints: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    summary: str = ""

