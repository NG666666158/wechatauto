from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._events import publish_event
from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, PrivacyPolicyData, RetentionApplyResultData
from wechat_ai.server.schemas.frontend import PrivacyPolicyPatchRequest

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/policy", response_model=ApiResponse[PrivacyPolicyData])
def get_privacy_policy(request: Request) -> dict[str, object]:
    return success_response(desktop_service(request).get_privacy_policy(), trace_id=request.state.trace_id)


@router.patch("/policy", response_model=ApiResponse[PrivacyPolicyData])
def update_privacy_policy(patch: PrivacyPolicyPatchRequest, request: Request) -> dict[str, object]:
    patch_data = patch.model_dump(exclude_none=True)
    data = desktop_service(request).update_privacy_policy(patch_data)
    publish_event(request, "log.event", {"event_type": "privacy.policy.updated", "changed_keys": sorted(patch_data)})
    return success_response(data, trace_id=request.state.trace_id)


@router.post("/apply-retention", response_model=ApiResponse[RetentionApplyResultData])
def apply_retention_policy(request: Request) -> dict[str, object]:
    data = desktop_service(request).apply_retention_policy()
    publish_event(request, "log.event", {"event_type": "privacy.retention.applied", "result": data})
    return success_response(data, trace_id=request.state.trace_id)
