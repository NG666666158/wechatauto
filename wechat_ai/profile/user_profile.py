from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UserProfile:
    user_id: str
    display_name: str = ""
    tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)
