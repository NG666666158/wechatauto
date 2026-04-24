from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import LOGS_DIR


RUNTIME_LOG_FILE = LOGS_DIR / "runtime_events.jsonl"
DEFAULT_LOG_MAX_BYTES = 1_000_000
DEFAULT_LOG_BACKUP_COUNT = 3

_INLINE_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret|authorization)\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)\bBearer\s+([A-Za-z0-9._-]+)"),
]


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sanitize_text(value: object, *, max_chars: int | None = None) -> str:
    text = str(value).strip()
    for pattern in _INLINE_SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            text = pattern.sub("Bearer [redacted]", text)
        else:
            text = pattern.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    if max_chars is not None and max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip() + "...(truncated)"
    return text


def _normalize_value(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _normalize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_value(item) for item in value]
    return value


class JsonlEventLogger:
    def __init__(
        self,
        path: Path | None = None,
        *,
        max_bytes: int = DEFAULT_LOG_MAX_BYTES,
        backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
    ) -> None:
        self.path = Path(path) if path is not None else RUNTIME_LOG_FILE
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def log_event(self, event_type: str, **fields: Any) -> dict[str, Any]:
        payload = {
            "timestamp": utc_timestamp(),
            "event_type": event_type,
            **{key: _normalize_value(value) for key, value in fields.items()},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload

    def _rotate_if_needed(self) -> None:
        if self.max_bytes <= 0 or self.backup_count <= 0 or not self.path.exists():
            return
        if self.path.stat().st_size < self.max_bytes:
            return
        oldest_backup = Path(f"{self.path}.{self.backup_count}")
        if oldest_backup.exists():
            oldest_backup.unlink()
        for index in range(self.backup_count - 1, 0, -1):
            source = Path(f"{self.path}.{index}")
            target = Path(f"{self.path}.{index + 1}")
            if source.exists():
                source.replace(target)
        current_bytes = self.path.read_bytes()
        backup_path = Path(f"{self.path}.1")
        backup_path.write_bytes(current_bytes)
        self.path.write_text("", encoding="utf-8")


def read_jsonl_events(path: Path | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path is not None else RUNTIME_LOG_FILE
    if not target.exists():
        return []
    events: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            events.append(json.loads(stripped))
    return events


def tail_jsonl_events(limit: int = 20, path: Path | None = None) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    events = read_jsonl_events(path=path)
    return events[-limit:]


def is_error_event(event: Mapping[str, Any]) -> bool:
    level = str(event.get("level") or "").strip().lower()
    if level:
        return level in {"error", "critical", "exception"}
    event_type = str(event.get("event_type") or "").lower()
    return "error" in event_type or bool(event.get("exception_type")) or bool(event.get("reason_code"))


def filter_log_events(
    events: Iterable[Mapping[str, Any]],
    *,
    event_type: str | None = None,
    trace_id: str | None = None,
    only_errors: bool = False,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for event in events:
        if event_type is not None and event.get("event_type") != event_type:
            continue
        if trace_id is not None and event.get("trace_id") != trace_id:
            continue
        if only_errors and not is_error_event(event):
            continue
        filtered.append(dict(event))
    return filtered


def summarize_log_events(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    recent_events = list(events)
    return {
        "recent_count": len(recent_events),
        "recent_error_count": sum(1 for event in recent_events if is_error_event(event)),
        "last_event_time": recent_events[-1].get("timestamp") if recent_events else None,
    }


def format_event_lines(events: Iterable[Mapping[str, Any]]) -> list[str]:
    return [json.dumps(dict(event), ensure_ascii=False, indent=2) for event in events]
