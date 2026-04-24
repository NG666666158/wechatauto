from __future__ import annotations

from datetime import datetime, timedelta

from .models import ScheduleBlock, ScheduleStatus, SettingsSnapshot


_DAY_TO_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class ScheduleManager:
    def evaluate(self, settings: SettingsSnapshot, *, now: datetime | None = None) -> ScheduleStatus:
        current = now or datetime.now()
        blocks = [block for block in settings.schedule_blocks if block.enabled]
        if not settings.schedule_enabled or not blocks:
            return ScheduleStatus(enabled=False, should_run=True, reason="schedule_disabled")

        active = self._find_active_block(blocks, current)
        if active is not None:
            return ScheduleStatus(
                enabled=True,
                should_run=True,
                active_block_label=active.label or f"{active.day_of_week} {active.start}-{active.end}",
                active_block_day=active.day_of_week,
                next_action="pause",
                next_transition_at=self._next_end_time(active, current).isoformat(),
                reason="within_schedule_block",
            )

        next_block, next_start = self._find_next_block(blocks, current)
        return ScheduleStatus(
            enabled=True,
            should_run=False,
            next_action="start",
            next_transition_at=next_start.isoformat() if next_start is not None else None,
            reason=f"waiting_for_{next_block.day_of_week}" if next_block is not None else "no_future_block",
        )

    def _find_active_block(self, blocks: list[ScheduleBlock], now: datetime) -> ScheduleBlock | None:
        return next((block for block in blocks if _matches_block(block, now)), None)

    def _find_next_block(self, blocks: list[ScheduleBlock], now: datetime) -> tuple[ScheduleBlock | None, datetime | None]:
        candidates: list[tuple[datetime, ScheduleBlock]] = []
        for block in blocks:
            start_time = _next_start_time(block, now)
            if start_time is not None:
                candidates.append((start_time, block))
        if not candidates:
            return None, None
        start_time, block = min(candidates, key=lambda item: item[0])
        return block, start_time

    def _next_end_time(self, block: ScheduleBlock, now: datetime) -> datetime:
        end_hour, end_minute = _parse_hhmm(block.end)
        return now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)


def _matches_block(block: ScheduleBlock, now: datetime) -> bool:
    block_index = _DAY_TO_INDEX.get(block.day_of_week)
    if block_index is None or block_index != now.weekday():
        return False
    start_hour, start_minute = _parse_hhmm(block.start)
    end_hour, end_minute = _parse_hhmm(block.end)
    start_dt = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end_dt = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    return start_dt <= now < end_dt


def _next_start_time(block: ScheduleBlock, now: datetime) -> datetime | None:
    block_index = _DAY_TO_INDEX.get(block.day_of_week)
    if block_index is None:
        return None
    start_hour, start_minute = _parse_hhmm(block.start)
    days_ahead = (block_index - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour_text, minute_text = str(value).split(":", 1)
    return int(hour_text), int(minute_text)
