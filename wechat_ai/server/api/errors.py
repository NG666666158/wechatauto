from __future__ import annotations

from fastapi import APIRouter, Request

from wechat_ai.server.core import error_catalog, success_response
from wechat_ai.server.schemas import ApiResponse, ErrorCatalogData

router = APIRouter(prefix="/errors", tags=["system"])


@router.get("/catalog", response_model=ApiResponse[ErrorCatalogData])
def get_error_catalog(request: Request) -> dict[str, object]:
    return success_response(error_catalog(), trace_id=request.state.trace_id)
