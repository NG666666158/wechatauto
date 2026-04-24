from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, DashboardSummaryData

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=ApiResponse[DashboardSummaryData])
def dashboard_summary(request: Request) -> dict[str, object]:
    service = desktop_service(request)
    return success_response(
        {
            "app": _to_dict(service.get_app_status()),
            "runtime": request.app.state.runtime_manager.status(),
            "knowledge": service.get_knowledge_status(),
            "pending": {
                "identity_drafts": len(service.list_identity_drafts()),
                "identity_candidates": len(service.list_identity_candidates()),
            },
        },
        trace_id=request.state.trace_id,
    )


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {}
