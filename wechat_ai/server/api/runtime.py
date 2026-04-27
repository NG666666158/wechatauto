from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._events import publish_event
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, RuntimeActionData, RuntimeBootstrapStartRequest, RuntimeStatusData
from wechat_ai.server.schemas.runtime import RuntimeStartRequest
from wechat_ai.server.services import RuntimeManager

router = APIRouter(prefix="/runtime", tags=["runtime"])


def _manager(request: Request) -> RuntimeManager:
    return request.app.state.runtime_manager


@router.get("/status", response_model=ApiResponse[RuntimeStatusData])
def runtime_status(request: Request) -> dict[str, object]:
    return success_response(_manager(request).status(), trace_id=request.state.trace_id)


@router.post("/start", response_model=ApiResponse[RuntimeActionData])
def runtime_start(payload: RuntimeStartRequest, request: Request) -> dict[str, object]:
    data = _manager(request).start(mode=payload.mode)
    publish_event(request, "runtime.status", data)
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/bootstrap-start", response_model=ApiResponse[RuntimeActionData])
def runtime_bootstrap_start(payload: RuntimeBootstrapStartRequest, request: Request) -> dict[str, object]:
    data = _manager(request).bootstrap_start(
        mode=payload.mode,
        ready_timeout_seconds=payload.ready_timeout_seconds,
        poll_interval_seconds=payload.poll_interval_seconds,
        narrator_settle_seconds=payload.narrator_settle_seconds,
        wait_for_ui_ready_before_guardian=True,
    )
    publish_event(request, "runtime.status", data)
    publish_event(
        request,
        "log.event",
        {
            "event_type": "runtime.bootstrap.completed",
            "state": data.get("state", "running"),
            "bootstrap": data.get("bootstrap", {}),
        },
    )
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/bootstrap-check", response_model=ApiResponse[RuntimeActionData])
def runtime_bootstrap_check(payload: RuntimeBootstrapStartRequest, request: Request) -> dict[str, object]:
    data = _manager(request).bootstrap_check(
        mode=payload.mode,
        ready_timeout_seconds=payload.ready_timeout_seconds,
        poll_interval_seconds=payload.poll_interval_seconds,
        narrator_settle_seconds=payload.narrator_settle_seconds,
        wait_for_ui_ready_before_guardian=True,
    )
    publish_event(
        request,
        "log.event",
        {
            "event_type": "runtime.bootstrap.checked",
            "state": data.get("state", "stopped"),
            "bootstrap": data.get("bootstrap", {}),
        },
    )
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/stop", response_model=ApiResponse[RuntimeActionData])
def runtime_stop(request: Request) -> dict[str, object]:
    data = _manager(request).stop()
    publish_event(request, "runtime.status", data)
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/force-stop", response_model=ApiResponse[RuntimeActionData])
def runtime_force_stop(request: Request) -> dict[str, object]:
    data = _manager(request).force_stop()
    publish_event(request, "runtime.status", data)
    publish_event(request, "log.event", {"event_type": "runtime.force_stopped", "state": data.get("state", "stopped")})
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/pause", response_model=ApiResponse[RuntimeActionData])
def runtime_pause(request: Request) -> dict[str, object]:
    data = _manager(request).pause()
    publish_event(request, "runtime.status", data)
    publish_event(request, "log.event", {"event_type": "runtime.paused", "state": data.get("state", "paused")})
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/restart", response_model=ApiResponse[RuntimeActionData])
def runtime_restart(payload: RuntimeStartRequest, request: Request) -> dict[str, object]:
    data = _manager(request).restart(mode=payload.mode)
    publish_event(request, "runtime.status", data)
    return success_response(data, trace_id=request.state.trace_id)
