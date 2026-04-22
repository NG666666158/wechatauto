from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AgentProfile:
    agent_id: str
    display_name: str = ""
    style_rules: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    forbidden_rules: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
