from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import DaemonStatus


class DaemonController:
    def __init__(self, state_path: Path) -> None:
        self.state_path = Path(state_path)

    def load_status(self) -> DaemonStatus:
        if not self.state_path.exists():
            return DaemonStatus()
        with self.state_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return DaemonStatus()
        return DaemonStatus(
            state=str(payload.get("state", "stopped")),
            pid=_optional_int(payload.get("pid")),
            run_silently=bool(payload.get("run_silently", True)),
            last_heartbeat=_optional_text(payload.get("last_heartbeat")),
            last_started_at=_optional_text(payload.get("last_started_at")),
            last_stopped_at=_optional_text(payload.get("last_stopped_at")),
            last_error=_optional_text(payload.get("last_error")),
            consecutive_errors=int(payload.get("consecutive_errors", 0)),
            retry_backoff_seconds=float(payload.get("retry_backoff_seconds", 0.0)),
            next_retry_at=_optional_text(payload.get("next_retry_at")),
            today_received=int(payload.get("today_received", 0)),
            today_replied=int(payload.get("today_replied", 0)),
        )

    def start(self, *, run_silently: bool = True, pid: int | None = None, now: datetime | None = None) -> DaemonStatus:
        status = self.load_status()
        status.state = "running"
        status.pid = pid
        status.run_silently = run_silently
        status.last_started_at = _now(now)
        status.last_error = None
        status.consecutive_errors = 0
        status.retry_backoff_seconds = 0.0
        status.next_retry_at = None
        self._save(status)
        return status

    def pause(self, *, now: datetime | None = None) -> DaemonStatus:
        status = self.load_status()
        status.state = "paused"
        status.last_stopped_at = _now(now)
        self._save(status)
        return status

    def stop(self, *, now: datetime | None = None) -> DaemonStatus:
        status = self.load_status()
        status.state = "stopped"
        status.pid = None
        status.last_stopped_at = _now(now)
        self._save(status)
        return status

    def record_heartbeat(self, *, now: datetime | None = None) -> DaemonStatus:
        status = self.load_status()
        status.last_heartbeat = _now(now)
        self._save(status)
        return status

    def record_loop_success(self) -> DaemonStatus:
        status = self.load_status()
        status.last_error = None
        status.consecutive_errors = 0
        status.retry_backoff_seconds = 0.0
        status.next_retry_at = None
        self._save(status)
        return status

    def record_error(
        self,
        *,
        exception_type: str,
        exception_message: str,
        base_backoff_seconds: float = 5.0,
        now: datetime | None = None,
    ) -> DaemonStatus:
        status = self.load_status()
        current_time = _as_datetime(now)
        status.last_error = f"{exception_type}: {exception_message}"
        status.consecutive_errors += 1
        status.retry_backoff_seconds = min(base_backoff_seconds * (2 ** (status.consecutive_errors - 1)), 60.0)
        status.next_retry_at = _iso(current_time + timedelta(seconds=status.retry_backoff_seconds))
        self._save(status)
        return status

    def record_reply_stats(self, *, received_delta: int = 0, replied_delta: int = 0) -> DaemonStatus:
        status = self.load_status()
        status.today_received += max(received_delta, 0)
        status.today_replied += max(replied_delta, 0)
        self._save(status)
        return status

    def _save(self, status: DaemonStatus) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(status), handle, ensure_ascii=False, indent=2)


def _optional_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now(value: datetime | None) -> str:
    return _iso(_as_datetime(value))
