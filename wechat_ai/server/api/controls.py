from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, ConversationControlData
from wechat_ai.server.schemas.frontend import ConversationControlPatchRequest

router = APIRouter(prefix="/controls", tags=["controls"])


@router.get("/conversations/{conversation_id}", response_model=ApiResponse[ConversationControlData])
def get_conversation_control(conversation_id: str, request: Request) -> dict[str, object]:
    return success_response(
        desktop_service(request).get_conversation_control(conversation_id),
        trace_id=request.state.trace_id,
    )


@router.patch("/conversations/{conversation_id}", response_model=ApiResponse[ConversationControlData])
def update_conversation_control(
    conversation_id: str,
    patch: ConversationControlPatchRequest,
    request: Request,
) -> dict[str, object]:
    return success_response(
        desktop_service(request).update_conversation_control(conversation_id, patch.model_dump(exclude_none=True)),
        trace_id=request.state.trace_id,
    )
