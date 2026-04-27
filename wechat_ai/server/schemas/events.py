from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventFieldSpecData(BaseModel):
    type: str = ""
    required: bool = True
    description: str = ""


class EventTypeContractData(BaseModel):
    type: str = ""
    description: str = ""
    payload_schema: dict[str, EventFieldSpecData] = Field(default_factory=dict)
    sample: dict[str, Any] = Field(default_factory=dict)


class EventContractData(BaseModel):
    contract_version: str = "p4-event-v1"
    envelope: dict[str, EventFieldSpecData] = Field(default_factory=dict)
    events: list[EventTypeContractData] = Field(default_factory=list)
