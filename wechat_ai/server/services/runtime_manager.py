from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from wechat_ai.app.service import DesktopAppService
from wechat_ai.server.core import ApiError, ErrorCode


RUNNING_STATES = {"starting", "running"}
STOPPED_STATES = {"idle", "stopped", "paused"}


class RuntimeManager:
    def __init__(self, desktop_service: DesktopAppService) -> None:
        self.desktop_service = desktop_service

    def status(self) -> dict[str, Any]:
        daemon = self.desktop_service.get_daemon_status()
        app_status = self.desktop_service.get_app_status()
        return {
            "state": str(daemon.get("state", "stopped")),
            "mode": "global",
            "running": str(daemon.get("state", "stopped")) in RUNNING_STATES,
            "daemon": daemon,
            "app": _to_dict(app_status),
        }

    def start(self, *, mode: str = "global") -> dict[str, Any]:
        normalized_mode = (mode or "global").strip().lower()
        if normalized_mode != "global":
            raise ApiError(
                ErrorCode.CONFIG_INVALID,
                "Only global runtime mode is supported in this phase",
                detail={"mode": mode, "supported_modes": ["global"]},
                status_code=400,
            )

        status = self.status()
        if status["state"] in RUNNING_STATES:
            raise ApiError(
                ErrorCode.RUNTIME_ALREADY_RUNNING,
                "Runtime is already running",
                detail={"state": status["state"]},
                status_code=409,
            )

        daemon = self.desktop_service.start_daemon()
        return {
            "state": str(daemon.get("state", "running")),
            "mode": normalized_mode,
            "running": True,
            "daemon": daemon,
        }

    def stop(self) -> dict[str, Any]:
        status = self.status()
        if status["state"] not in RUNNING_STATES:
            raise ApiError(
                ErrorCode.RUNTIME_NOT_RUNNING,
                "Runtime is not running",
                detail={"state": status["state"]},
                status_code=409,
            )

        daemon = self.desktop_service.stop_daemon()
        return {
            "state": str(daemon.get("state", "stopped")),
            "mode": status["mode"],
            "running": False,
            "daemon": daemon,
        }

    def restart(self, *, mode: str = "global") -> dict[str, Any]:
        status = self.status()
        if status["state"] in RUNNING_STATES:
            self.desktop_service.stop_daemon()
        return self.start(mode=mode)


def _to_dict(value: object) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {}
