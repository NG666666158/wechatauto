from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse

router = APIRouter(prefix="/shell", tags=["shell"])


@router.get("/tray-state", response_model=ApiResponse[dict[str, object]])
def get_tray_state(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_tray_state(), trace_id=request.state.trace_id)


@router.get("/schedule-status", response_model=ApiResponse[dict[str, object]])
def get_schedule_status(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_schedule_status(), trace_id=request.state.trace_id)


@router.post("/schedule/tick", response_model=ApiResponse[dict[str, object]])
def apply_schedule_tick(request: Request) -> dict[str, object]:
    data = desktop_service(request).apply_schedule_tick()
    return success_response(data, trace_id=request.state.trace_id)
