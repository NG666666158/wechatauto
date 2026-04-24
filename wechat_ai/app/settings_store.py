from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .models import ScheduleBlock, SettingsSnapshot, WorkHours


class DesktopSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> SettingsSnapshot:
        if not self.path.exists():
            return SettingsSnapshot()
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return self._deserialize(payload if isinstance(payload, dict) else {})

    def update(self, patch: Mapping[str, object]) -> SettingsSnapshot:
        current = self.load()
        updated = self._apply_patch(current, patch)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(updated), handle, ensure_ascii=False, indent=2)
        return updated

    def _deserialize(self, payload: Mapping[str, Any]) -> SettingsSnapshot:
        work_hours_payload = payload.get("work_hours", {})
        if not isinstance(work_hours_payload, Mapping):
            work_hours_payload = {}
        schedule_blocks_payload = payload.get("schedule_blocks", [])
        if not isinstance(schedule_blocks_payload, list):
            schedule_blocks_payload = []
        return SettingsSnapshot(
            auto_reply_enabled=bool(payload.get("auto_reply_enabled", True)),
            reply_style=str(payload.get("reply_style", "自然友好")),
            new_customer_auto_create=bool(payload.get("new_customer_auto_create", True)),
            sensitive_message_review=bool(payload.get("sensitive_message_review", True)),
            work_hours=WorkHours(
                enabled=bool(work_hours_payload.get("enabled", True)),
                start=str(work_hours_payload.get("start", "09:00")),
                end=str(work_hours_payload.get("end", "18:00")),
            ),
            knowledge_chunk_size=int(payload.get("knowledge_chunk_size", 1000)),
            knowledge_chunk_overlap=int(payload.get("knowledge_chunk_overlap", 200)),
            run_silently=bool(payload.get("run_silently", True)),
            esc_action=str(payload.get("esc_action", "pause")),
            schedule_enabled=bool(payload.get("schedule_enabled", False)),
            schedule_blocks=[
                ScheduleBlock(
                    day_of_week=str(item.get("day_of_week", "")),
                    start=str(item.get("start", "09:00")),
                    end=str(item.get("end", "18:00")),
                    label=str(item.get("label", "")),
                    enabled=bool(item.get("enabled", True)),
                )
                for item in schedule_blocks_payload
                if isinstance(item, Mapping)
            ],
        )

    def _apply_patch(self, current: SettingsSnapshot, patch: Mapping[str, object]) -> SettingsSnapshot:
        payload = asdict(current)
        for key, value in patch.items():
            if key == "work_hours" and isinstance(value, Mapping):
                merged_work_hours = dict(payload["work_hours"])
                for nested_key, nested_value in value.items():
                    if nested_key in merged_work_hours:
                        merged_work_hours[nested_key] = nested_value
                payload["work_hours"] = merged_work_hours
            elif key == "schedule_blocks" and isinstance(value, list):
                payload["schedule_blocks"] = value
            elif key in payload:
                payload[key] = value
        return self._deserialize(payload)
