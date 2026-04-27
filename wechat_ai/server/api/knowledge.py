from __future__ import annotations

from fastapi import APIRouter, Query, Request

from wechat_ai.server.api._events import publish_event
from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import (
    ApiResponse,
    KnowledgeImportResultData,
    KnowledgeSearchResultData,
    KnowledgeStatusData,
    WebKnowledgeBuildResultData,
)
from wechat_ai.server.schemas.frontend import KnowledgeImportRequest, WebKnowledgeBuildRequest

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/status", response_model=ApiResponse[KnowledgeStatusData])
def knowledge_status(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_knowledge_status(), trace_id=request.state.trace_id)


@router.get("/search", response_model=ApiResponse[list[KnowledgeSearchResultData]])
def search_knowledge(request: Request, q: str = Query(...), limit: int = Query(3, ge=1, le=20)) -> dict[str, object]:
    return success_response(desktop_service(request).search_knowledge(q, limit=limit), trace_id=request.state.trace_id)


@router.post("/import", response_model=ApiResponse[KnowledgeImportResultData])
def import_knowledge(payload: KnowledgeImportRequest, request: Request) -> dict[str, object]:
    data = desktop_service(request).import_knowledge_files(payload.file_paths)
    publish_event(
        request,
        "knowledge.progress",
        {
            "status": "imported",
            "file_count": len(payload.file_paths),
            "index_rebuilt": data.get("index_rebuilt", False) if isinstance(data, dict) else False,
        },
    )
    return success_response(
        data,
        trace_id=request.state.trace_id,
    )


@router.post("/web-build", response_model=ApiResponse[WebKnowledgeBuildResultData])
def build_web_knowledge(payload: WebKnowledgeBuildRequest, request: Request) -> dict[str, object]:
    data = desktop_service(request).build_web_knowledge_from_documents(
        payload.file_paths,
        search_limit=payload.search_limit,
    )
    publish_event(
        request,
        "knowledge.progress",
        {
            "status": data.get("status", "built") if isinstance(data, dict) else "built",
            "file_count": len(payload.file_paths),
            "search_limit": payload.search_limit,
        },
    )
    return success_response(
        data,
        trace_id=request.state.trace_id,
    )
