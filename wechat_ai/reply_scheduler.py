from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PendingReplyBatch:
    session_name: str
    chat_type: str
    sender_name: str
    messages: list[str]
    contexts: list[str]
    deadline: float
    first_seen_at: float
    last_seen_at: float


@dataclass(slots=True)
class _PendingState:
    session_name: str
    chat_type: str
    sender_name: str
    messages: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    deadline: float = 0.0
    first_seen_at: float = 0.0
    last_seen_at: float = 0.0

    def to_batch(self) -> PendingReplyBatch:
        return PendingReplyBatch(
            session_name=self.session_name,
            chat_type=self.chat_type,
            sender_name=self.sender_name,
            messages=list(self.messages),
            contexts=list(self.contexts),
            deadline=self.deadline,
            first_seen_at=self.first_seen_at,
            last_seen_at=self.last_seen_at,
        )


class ReplyScheduler:
    def __init__(
        self,
        *,
        merge_window_seconds: float = 2.0,
        max_messages_per_batch: int = 5,
        min_reply_interval_seconds: float | None = None,
    ) -> None:
        if merge_window_seconds < 0:
            raise ValueError("merge_window_seconds must be non-negative")
        if max_messages_per_batch < 1:
            raise ValueError("max_messages_per_batch must be at least 1")
        if min_reply_interval_seconds is not None and min_reply_interval_seconds < 0:
            raise ValueError("min_reply_interval_seconds must be non-negative")

        self.merge_window_seconds = float(merge_window_seconds)
        self.max_messages_per_batch = int(max_messages_per_batch)
        self.min_reply_interval_seconds = (
            None if min_reply_interval_seconds is None else float(min_reply_interval_seconds)
        )
        self._pending: dict[tuple[str, str], _PendingState] = {}
        self._last_reply_at: dict[tuple[str, str], float] = {}

    def add_message(
        self,
        session_name: str,
        chat_type: str,
        text: str,
        contexts: list[str],
        sender_name: str,
        now: float,
    ) -> list[PendingReplyBatch]:
        key = (session_name, chat_type)
        ready: list[PendingReplyBatch] = []
        existing = self._pending.get(key)

        if existing is not None and now >= self._ready_at(key, existing):
            ready.append(self._pop_ready(key, now))
            existing = None

        if existing is None:
            self._pending[key] = _PendingState(
                session_name=session_name,
                chat_type=chat_type,
                sender_name=sender_name,
                messages=[text],
                contexts=list(contexts),
                deadline=now + self.merge_window_seconds,
                first_seen_at=now,
                last_seen_at=now,
            )
        else:
            existing.sender_name = sender_name
            existing.messages.append(text)
            existing.contexts.extend(contexts)
            existing.last_seen_at = now
            existing.deadline = now + self.merge_window_seconds

        pending = self._pending[key]
        if len(pending.messages) >= self.max_messages_per_batch and now >= self._rate_ready_at(key):
            ready.append(self._pop_ready(key, now))

        return ready

    def drain_ready(self, now: float) -> list[PendingReplyBatch]:
        ready: list[PendingReplyBatch] = []
        for key, pending in list(self._pending.items()):
            if now >= self._ready_at(key, pending):
                ready.append(self._pop_ready(key, now))
        return ready

    def flush_all(self, reason: str) -> list[PendingReplyBatch]:
        del reason
        ready: list[PendingReplyBatch] = []
        for key in list(self._pending):
            pending = self._pending.pop(key)
            batch = pending.to_batch()
            ready.append(batch)
            self._last_reply_at[key] = batch.last_seen_at
        return ready

    def _ready_at(self, key: tuple[str, str], pending: _PendingState) -> float:
        return max(pending.deadline, self._rate_ready_at(key))

    def _rate_ready_at(self, key: tuple[str, str]) -> float:
        if self.min_reply_interval_seconds is None:
            return float("-inf")
        last_reply_at = self._last_reply_at.get(key)
        if last_reply_at is None:
            return float("-inf")
        return last_reply_at + self.min_reply_interval_seconds

    def _pop_ready(self, key: tuple[str, str], now: float) -> PendingReplyBatch:
        pending = self._pending.pop(key)
        self._last_reply_at[key] = now
        return pending.to_batch()
