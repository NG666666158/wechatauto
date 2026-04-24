from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, IdentityCandidateData, IdentityDraftData, SelfIdentityData
from wechat_ai.server.schemas.frontend import SelfIdentityPatchRequest

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/drafts", response_model=ApiResponse[list[IdentityDraftData]])
def list_identity_drafts(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).list_identity_drafts(), trace_id=request.state.trace_id)


@router.get("/candidates", response_model=ApiResponse[list[IdentityCandidateData]])
def list_identity_candidates(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).list_identity_candidates(), trace_id=request.state.trace_id)


@router.get("/self/global", response_model=ApiResponse[SelfIdentityData])
def get_global_self_identity(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_global_self_identity(), trace_id=request.state.trace_id)


@router.patch("/self/global", response_model=ApiResponse[SelfIdentityData])
def update_global_self_identity(patch: SelfIdentityPatchRequest, request: Request) -> dict[str, object]:
    return success_response(
        desktop_service(request).update_global_self_identity(patch.model_dump(exclude_none=True)),
        trace_id=request.state.trace_id,
    )
