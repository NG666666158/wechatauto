from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Request

from wechat_ai.server.api._service import desktop_service
from wechat_ai.server.core import success_response
from wechat_ai.server.schemas import ApiResponse, CustomerData

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=ApiResponse[list[CustomerData]])
def list_customers(request: Request) -> dict[str, object]:
    records = [_to_dict(item) for item in desktop_service(request).list_customers()]
    return success_response(records, trace_id=request.state.trace_id)


@router.get("/{customer_id}", response_model=ApiResponse[CustomerData])
def get_customer(customer_id: str, request: Request) -> dict[str, object]:
    return success_response(_to_dict(desktop_service(request).get_customer(customer_id)), trace_id=request.state.trace_id)


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {}
