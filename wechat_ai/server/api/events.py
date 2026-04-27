from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from wechat_ai.server.services.events import EventBus, format_sse_event

router = APIRouter(tags=["events"])


def _event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


@router.get("/events")
async def stream_events(
    request: Request,
    replay: int = Query(0, ge=0, le=100),
    once: bool = False,
    heartbeat_seconds: float = Query(15.0, ge=1.0, le=300.0),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        bus = _event_bus(request)
        replay_events, subscription = bus.subscribe(replay=replay)
        try:
            for event in replay_events:
                yield format_sse_event(event)
            if once:
                return
            while not await request.is_disconnected():
                event = await bus.next_event(subscription, timeout=heartbeat_seconds)
                if event is None:
                    yield ": heartbeat\n\n"
                    continue
                yield format_sse_event(event)
        finally:
            bus.unsubscribe(subscription)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
