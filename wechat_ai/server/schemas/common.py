from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiErrorPayload(BaseModel):
    code: str
    message: str
    detail: Any = ""


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiErrorPayload | None = None
    trace_id: str = Field(default="")


class HttpErrorCodeData(BaseModel):
    code: str = ""
    http_status: int = 400
    message: str = ""
    description: str = ""


class BusinessStatusData(BaseModel):
    status: str = ""
    http_status: int = 200
    description: str = ""


class BusinessReasonCodeData(BaseModel):
    code: str = ""
    status: str = ""
    description: str = ""


class ErrorCatalogData(BaseModel):
    http_errors: list[HttpErrorCodeData] = Field(default_factory=list)
    send_reply_statuses: list[BusinessStatusData] = Field(default_factory=list)
    send_reply_reason_codes: list[BusinessReasonCodeData] = Field(default_factory=list)
