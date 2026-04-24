from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ApiResponse[dict[str, object]])
def health(request: Request) -> dict[str, object]:
    service = request.app.state.desktop_service
    app_status = service.get_app_status()
    daemon_status = service.get_daemon_status()
    knowledge_status = service.get_knowledge_status()
    data = {
        "status": "ok",
        "service": "wechat_ai_server",
        "runtime": {
            "daemon_state": app_status.daemon_state,
            "auto_reply_enabled": app_status.auto_reply_enabled,
            "last_heartbeat": app_status.last_heartbeat,
        },
        "daemon": daemon_status,
        "knowledge": {
            "ready": knowledge_status.get("ready", False),
            "index_path": knowledge_status.get("index_path", ""),
        },
    }
    return success_response(data, trace_id=request.state.trace_id)
