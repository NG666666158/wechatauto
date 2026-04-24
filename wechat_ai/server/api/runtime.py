from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, RuntimeActionData, RuntimeStatusData
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
    return success_response(_manager(request).start(mode=payload.mode), trace_id=request.state.trace_id)


@router.post("/stop", response_model=ApiResponse[RuntimeActionData])
def runtime_stop(request: Request) -> dict[str, object]:
    return success_response(_manager(request).stop(), trace_id=request.state.trace_id)


@router.post("/restart", response_model=ApiResponse[RuntimeActionData])
def runtime_restart(payload: RuntimeStartRequest, request: Request) -> dict[str, object]:
    return success_response(_manager(request).restart(mode=payload.mode), trace_id=request.state.trace_id)
