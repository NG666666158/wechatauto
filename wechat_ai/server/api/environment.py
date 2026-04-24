from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, WechatEnvironmentData

router = APIRouter(prefix="/environment", tags=["environment"])


@router.get("/wechat", response_model=ApiResponse[WechatEnvironmentData])
def wechat_environment(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_wechat_environment_status(), trace_id=request.state.trace_id)
