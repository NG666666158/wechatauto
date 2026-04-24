from __future__ import annotations

from typing import Any

from .errors import ErrorCode


def success_response(data: Any = None, *, trace_id: str = "") -> dict[str, Any]:
    return {
        "success": True,
        "data": data if data is not None else {},
        "error": None,
        "trace_id": trace_id,
    }


def fail_response(
    *,
    code: ErrorCode,
    message: str,
    trace_id: str = "",
    detail: Any = "",
) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code.value,
            "message": message,
            "detail": detail,
        },
        "trace_id": trace_id,
    }
