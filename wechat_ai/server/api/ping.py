from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse

router = APIRouter(tags=["system"])


@router.get("/ping", response_model=ApiResponse[dict[str, object]])
def ping(request: Request) -> dict[str, object]:
    return success_response(
        {
            "pong": True,
            "service": "wechat_ai_server",
        },
        trace_id=request.state.trace_id,
    )
