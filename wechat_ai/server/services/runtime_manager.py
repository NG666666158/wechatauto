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

    def bootstrap_start(
        self,
        *,
        mode: str = "global",
        ready_timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 1.0,
        narrator_settle_seconds: float = 10.0,
        wait_for_ui_ready_before_guardian: bool = False,
    ) -> dict[str, Any]:
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

        bootstrap = self.desktop_service.bootstrap_wechat_for_web_start(
            ready_timeout_seconds=ready_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            narrator_settle_seconds=narrator_settle_seconds,
            wait_for_ui_ready_before_guardian=wait_for_ui_ready_before_guardian,
        )
        if not bool(bootstrap.get("ok")):
            raise ApiError(
                ErrorCode.WECHAT_WINDOW_NOT_FOUND,
                str(bootstrap.get("message") or "WeChat bootstrap did not reach ready state"),
                detail=bootstrap,
                status_code=409,
            )

        daemon = self.desktop_service.start_daemon()
        return {
            "state": str(daemon.get("state", "running")),
            "mode": normalized_mode,
            "running": True,
            "daemon": daemon,
            "bootstrap": bootstrap,
        }

    def bootstrap_check(
        self,
        *,
        mode: str = "global",
        ready_timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 1.0,
        narrator_settle_seconds: float = 10.0,
        wait_for_ui_ready_before_guardian: bool = False,
    ) -> dict[str, Any]:
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

        bootstrap = self.desktop_service.bootstrap_wechat_for_web_start(
            ready_timeout_seconds=ready_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            narrator_settle_seconds=narrator_settle_seconds,
            wait_for_ui_ready_before_guardian=wait_for_ui_ready_before_guardian,
        )
        if not bool(bootstrap.get("ok")):
            raise ApiError(
                ErrorCode.WECHAT_WINDOW_NOT_FOUND,
                str(bootstrap.get("message") or "WeChat bootstrap did not reach ready state"),
                detail=bootstrap,
                status_code=409,
            )

        daemon = self.desktop_service.get_daemon_status()
        return {
            "state": str(daemon.get("state", "stopped")),
            "mode": normalized_mode,
            "running": False,
            "daemon": daemon,
            "bootstrap": bootstrap,
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

    def force_stop(self) -> dict[str, Any]:
        daemon = self.desktop_service.force_stop_daemon()
        return {
            "state": str(daemon.get("state", "stopped")),
            "mode": "global",
            "running": False,
            "daemon": daemon,
        }

    def pause(self) -> dict[str, Any]:
        status = self.status()
        if status["state"] not in RUNNING_STATES:
            raise ApiError(
                ErrorCode.RUNTIME_NOT_RUNNING,
                "Runtime is not running",
                detail={"state": status["state"]},
                status_code=409,
            )

        daemon = self.desktop_service.pause_daemon()
        return {
            "state": str(daemon.get("state", "paused")),
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
