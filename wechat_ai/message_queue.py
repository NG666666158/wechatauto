from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Literal


ChatType = Literal["friend", "group"]
MessageSource = Literal["unread", "active"]


@dataclass(slots=True)
class IncomingMessageEvent:
    session_name: str
    chat_type: ChatType
    text: str
    contexts: list[str] = field(default_factory=list)
    sender_name: str = ""
    source: MessageSource = "unread"
    signature: str = ""
    captured_at: float = 0.0

    def __post_init__(self) -> None:
        if self.chat_type not in ("friend", "group"):
            raise ValueError("chat_type must be 'friend' or 'group'")
        if self.source not in ("unread", "active"):
            raise ValueError("source must be 'unread' or 'active'")
        if not self.signature:
            raise ValueError("signature is required")
        self.contexts = list(self.contexts)


@dataclass(slots=True)
class MessageEventBatch:
    session_name: str
    chat_type: ChatType
    text: str
    contexts: list[str]
    sender_name: str
    source: MessageSource
    signature: str
    signatures: list[str]
    captured_at: float
    events: list[IncomingMessageEvent]


class MessageEventQueue:
    def __init__(self, seen_ttl_seconds: float = 300.0, seen_limit: int = 1000) -> None:
        if seen_ttl_seconds < 0:
            raise ValueError("seen_ttl_seconds must be non-negative")
        if seen_limit < 1:
            raise ValueError("seen_limit must be at least 1")
        self._seen_ttl_seconds = seen_ttl_seconds
        self._seen_limit = seen_limit
        self._events_by_session: OrderedDict[str, list[IncomingMessageEvent]] = OrderedDict()
        self._queued_signatures: set[str] = set()
        self._seen_signatures: OrderedDict[str, float] = OrderedDict()

    def enqueue_many(self, events: list[IncomingMessageEvent]) -> int:
        accepted = 0
        for event in events:
            self._prune_seen(event.captured_at)
            if event.signature in self._queued_signatures or event.signature in self._seen_signatures:
                continue
            self._events_by_session.setdefault(event.session_name, []).append(event)
            self._queued_signatures.add(event.signature)
            self._remember_signature(event.signature, event.captured_at)
            accepted += 1
        return accepted

    def drain_ready(self, now: float) -> list[MessageEventBatch]:
        self._prune_seen(now)
        batches: list[MessageEventBatch] = []
        empty_sessions: list[str] = []

        for session_name, events in self._events_by_session.items():
            ready_events = [event for event in events if event.captured_at <= now]
            if not ready_events:
                continue

            batches.append(self._build_batch(session_name, ready_events))
            ready_signatures = {event.signature for event in ready_events}
            for signature in ready_signatures:
                self._queued_signatures.discard(signature)
            remaining_events = [event for event in events if event.signature not in ready_signatures]
            if remaining_events:
                self._events_by_session[session_name] = remaining_events
            else:
                empty_sessions.append(session_name)

        for session_name in empty_sessions:
            self._events_by_session.pop(session_name, None)

        return batches

    def flush_all(self) -> list[MessageEventBatch]:
        batches = [
            self._build_batch(session_name, events)
            for session_name, events in self._events_by_session.items()
            if events
        ]
        self._events_by_session.clear()
        self._queued_signatures.clear()
        return batches

    def _build_batch(
        self, session_name: str, events: list[IncomingMessageEvent]
    ) -> MessageEventBatch:
        ordered_events = sorted(events, key=lambda event: event.captured_at)
        latest_event = ordered_events[-1]
        signatures = [event.signature for event in ordered_events]
        return MessageEventBatch(
            session_name=session_name,
            chat_type=latest_event.chat_type,
            text="\n".join(event.text for event in ordered_events),
            contexts=list(latest_event.contexts),
            sender_name=latest_event.sender_name,
            source=latest_event.source,
            signature="|".join(signatures),
            signatures=signatures,
            captured_at=latest_event.captured_at,
            events=ordered_events,
        )

    def _remember_signature(self, signature: str, seen_at: float) -> None:
        self._seen_signatures[signature] = seen_at
        self._seen_signatures.move_to_end(signature)
        while len(self._seen_signatures) > self._seen_limit:
            self._seen_signatures.popitem(last=False)

    def _prune_seen(self, now: float) -> None:
        expired_signatures = [
            signature
            for signature, seen_at in self._seen_signatures.items()
            if now - seen_at > self._seen_ttl_seconds
        ]
        for signature in expired_signatures:
            if signature not in self._queued_signatures:
                self._seen_signatures.pop(signature, None)
