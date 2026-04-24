from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import (
    ApiResponse,
    ConversationDetailData,
    ConversationListItemData,
    ReplySuggestionData,
    SendReplyResultData,
)
from wechat_ai.server.schemas.frontend import ReplySuggestionRequest, SendReplyRequest

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ApiResponse[list[ConversationListItemData]])
def list_conversations(request: Request) -> dict[str, object]:
    items = [_to_dict(item) for item in desktop_service(request).list_conversations()]
    return success_response(items, trace_id=request.state.trace_id)


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetailData])
def get_conversation(conversation_id: str, request: Request) -> dict[str, object]:
    return success_response(
        desktop_service(request).get_conversation(conversation_id),
        trace_id=request.state.trace_id,
    )


@router.post("/{conversation_id}/suggest", response_model=ApiResponse[ReplySuggestionData])
def suggest_reply(
    conversation_id: str,
    payload: ReplySuggestionRequest,
    request: Request,
) -> dict[str, object]:
    return success_response(
        _to_dict(desktop_service(request).suggest_reply(conversation_id, payload.message_text)),
        trace_id=request.state.trace_id,
    )


@router.post("/{conversation_id}/send", response_model=ApiResponse[SendReplyResultData])
def send_reply(
    conversation_id: str,
    payload: SendReplyRequest,
    request: Request,
) -> dict[str, object]:
    return success_response(
        desktop_service(request).send_reply(conversation_id, payload.text),
        trace_id=request.state.trace_id,
    )


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {}
