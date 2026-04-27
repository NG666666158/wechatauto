from __future__ import annotations

from fastapi import APIRouter, Query, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import (
    ApiResponse,
    KnowledgeAcceptanceSnapshotData,
    PromptAcceptancePreviewData,
)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/prompt-preview", response_model=ApiResponse[PromptAcceptancePreviewData])
def prompt_preview(
    request: Request,
    user_id: str = Query(..., min_length=1),
    latest_message: str = Query(..., min_length=1, max_length=8000),
    relationship_to_me: str | None = Query(None, max_length=64),
    display_name: str = Query("", max_length=64),
    tags: list[str] | None = Query(None),
    knowledge_limit: int = Query(3, ge=1, le=10),
    scene: str = Query("friend", pattern="^(friend|group)$"),
) -> dict[str, object]:
    data = desktop_service(request).build_prompt_acceptance_preview(
        user_id,
        latest_message=latest_message,
        tags=tags,
        display_name=display_name,
        relationship_to_me=relationship_to_me,
        knowledge_limit=knowledge_limit,
        scene=scene,
    )
    return success_response(data, trace_id=request.state.trace_id)


@router.get("/knowledge-acceptance", response_model=ApiResponse[KnowledgeAcceptanceSnapshotData])
def knowledge_acceptance(
    request: Request,
    q: str = Query(..., min_length=1, max_length=8000),
    imported_files: list[str] | None = Query(None),
) -> dict[str, object]:
    data = desktop_service(request).build_knowledge_acceptance_snapshot(
        q,
        imported_files=imported_files,
    )
    return success_response(data, trace_id=request.state.trace_id)
