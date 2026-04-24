from __future__ import annotations

from fastapi import APIRouter, Query, Request

from wechat_ai.logging_utils import filter_log_events, summarize_log_events
from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, LogsSummaryData

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/recent", response_model=ApiResponse[list[dict[str, object]]])
def recent_logs(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    event_type: str | None = Query(None, min_length=1),
    trace_id: str | None = Query(None, min_length=1),
    only_errors: bool = False,
) -> dict[str, object]:
    events = desktop_service(request).get_recent_logs(limit=limit)
    filtered_events = filter_log_events(
        events,
        event_type=event_type,
        trace_id=trace_id,
        only_errors=only_errors,
    )
    return success_response(filtered_events, trace_id=request.state.trace_id)


@router.get("/summary", response_model=ApiResponse[LogsSummaryData])
def logs_summary(request: Request, limit: int = Query(20, ge=1, le=200)) -> dict[str, object]:
    events = desktop_service(request).get_recent_logs(limit=limit)
    return success_response(summarize_log_events(events), trace_id=request.state.trace_id)
