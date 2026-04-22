from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SummaryMemory:
    text: str
    updated_at: str
