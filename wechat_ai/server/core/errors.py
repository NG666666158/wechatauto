from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    CONFIG_INVALID = "CONFIG_INVALID"
    REQUEST_INVALID = "REQUEST_INVALID"
    MODEL_API_FAILED = "MODEL_API_FAILED"
    WECHAT_WINDOW_NOT_FOUND = "WECHAT_WINDOW_NOT_FOUND"
    WECHAT_NOT_LOGIN = "WECHAT_NOT_LOGIN"
    RUNTIME_ALREADY_RUNNING = "RUNTIME_ALREADY_RUNNING"
    RUNTIME_NOT_RUNNING = "RUNTIME_NOT_RUNNING"
    KNOWLEDGE_INDEX_MISSING = "KNOWLEDGE_INDEX_MISSING"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ApiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        detail: Any = "",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
