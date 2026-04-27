from __future__ import annotations

from typing import Any

from fastapi import Request


def publish_event(request: Request, event_type: str, data: dict[str, Any]) -> None:
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus is None:
        return
    event_bus.publish(event_type, data, trace_id=getattr(request.state, "trace_id", ""))
