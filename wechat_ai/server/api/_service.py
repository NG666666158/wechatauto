from __future__ import annotations

from typing import Any

from fastapi import Request


def desktop_service(request: Request) -> Any:
    return request.app.state.desktop_service
