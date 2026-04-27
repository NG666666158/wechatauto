from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from threading import Lock
from uuid import uuid4
from typing import Any

from wechat_ai.logging_utils import is_error_event


@dataclass(slots=True)
class EventSubscription:
    token: int
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]]


class EventBus:
    def __init__(self, *, max_events: int = 500) -> None:
        self._events: deque[tuple[int, dict[str, Any]]] = deque(maxlen=max_events)
        self._lock = Lock()
        self._next_sequence = 0
        self._next_subscription_token = 0
        self._subscriptions: dict[int, EventSubscription] = {}

    def publish(self, event_type: str, data: dict[str, Any] | None = None, *, trace_id: str = "") -> dict[str, Any]:
        event = {
            "id": uuid4().hex,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
            "trace_id": trace_id,
        }
        with self._lock:
            self._next_sequence += 1
            self._events.append((self._next_sequence, event))
            subscriptions = list(self._subscriptions.values())
        stale_tokens: list[int] = []
        for subscription in subscriptions:
            try:
                subscription.loop.call_soon_threadsafe(subscription.queue.put_nowait, dict(event))
            except RuntimeError:
                stale_tokens.append(subscription.token)
        for token in stale_tokens:
            self.unsubscribe_by_token(token)
        return dict(event)

    def latest_sequence(self) -> int:
        with self._lock:
            return self._next_sequence

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._lock:
            events = list(self._events)
        return [dict(event) for _sequence, event in events[-limit:]]

    def subscribe(self, *, replay: int = 0) -> tuple[list[dict[str, Any]], EventSubscription]:
        replay_count = max(int(replay), 0)
        loop = asyncio.get_running_loop()
        subscription = EventSubscription(
            token=0,
            loop=loop,
            queue=asyncio.Queue(),
        )
        with self._lock:
            self._next_subscription_token += 1
            subscription.token = self._next_subscription_token
            self._subscriptions[subscription.token] = subscription
            replay_events = [dict(event) for _sequence, event in list(self._events)[-replay_count:]]
        return replay_events, subscription

    async def next_event(self, subscription: EventSubscription, *, timeout: float) -> dict[str, Any] | None:
        safe_timeout = max(float(timeout), 0.0)
        try:
            return await asyncio.wait_for(subscription.queue.get(), timeout=safe_timeout)
        except asyncio.TimeoutError:
            return None

    def unsubscribe(self, subscription: EventSubscription) -> None:
        self.unsubscribe_by_token(subscription.token)

    def unsubscribe_by_token(self, token: int) -> None:
        if not token:
            return
        with self._lock:
            self._subscriptions.pop(token, None)


class RuntimeEventRelay:
    def __init__(self, *, log_limit: int = 50, max_seen_keys: int = 1000) -> None:
        self._log_limit = log_limit
        self._seen_log_keys: deque[str] = deque(maxlen=max_seen_keys)
        self._seen_log_key_set: set[str] = set()
        self._last_environment_signature: str | None = None
        self._last_environment_snapshot: dict[str, Any] | None = None

    def sync(
        self,
        desktop_service: Any,
        event_bus: EventBus,
        *,
        trace_id: str = "",
        include_environment: bool = False,
    ) -> None:
        self._sync_recent_logs(desktop_service, event_bus, trace_id=trace_id)
        if include_environment:
            self._sync_environment(desktop_service, event_bus, trace_id=trace_id)

    def _sync_recent_logs(self, desktop_service: Any, event_bus: EventBus, *, trace_id: str) -> None:
        try:
            recent_logs = desktop_service.get_recent_logs(limit=self._log_limit)
        except Exception:
            return
        if not isinstance(recent_logs, list):
            return

        for raw_event in recent_logs:
            if not isinstance(raw_event, Mapping):
                continue
            event = {str(key): value for key, value in raw_event.items()}
            event_key = self._build_log_key(event)
            if self._has_seen_log_key(event_key):
                continue
            self._remember_log_key(event_key)

            log_payload = self._normalize_log_payload(event)
            effective_trace_id = str(log_payload.get("trace_id") or trace_id)
            event_bus.publish("log.event", log_payload, trace_id=effective_trace_id)

            typed_event = self._map_runtime_log_event(log_payload)
            if typed_event is not None:
                event_bus.publish(typed_event["type"], typed_event["data"], trace_id=effective_trace_id)

            if is_error_event(log_payload):
                event_bus.publish(
                    "error",
                    {
                        "code": str(log_payload.get("reason_code") or log_payload.get("event_type") or "RUNTIME_ERROR"),
                        "message": str(log_payload.get("message") or log_payload.get("event_type") or "Runtime error"),
                        "detail": log_payload,
                    },
                    trace_id=effective_trace_id,
                )

    def _sync_environment(self, desktop_service: Any, event_bus: EventBus, *, trace_id: str) -> None:
        try:
            status = desktop_service.get_wechat_environment_status()
        except Exception:
            return
        if not isinstance(status, Mapping):
            return

        snapshot = {str(key): value for key, value in status.items()}
        signature = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        if self._last_environment_signature is None:
            self._last_environment_signature = signature
            self._last_environment_snapshot = snapshot
            return
        if signature == self._last_environment_signature:
            return

        previous_snapshot = self._last_environment_snapshot or {}
        self._last_environment_signature = signature
        self._last_environment_snapshot = snapshot

        changes = _diff_environment(previous_snapshot, snapshot)
        event_bus.publish(
            "log.event",
            {
                "level": "warn" if not bool(snapshot.get("ui_ready")) else "info",
                "event_type": "window.environment.changed",
                "message": _build_environment_change_message(snapshot, changes),
                "changes": changes,
                "snapshot": snapshot,
            },
            trace_id=trace_id,
        )

    def _build_log_key(self, event: Mapping[str, Any]) -> str:
        key_parts = (
            str(event.get("timestamp") or ""),
            str(event.get("event_type") or ""),
            str(event.get("conversation_id") or event.get("chat_id") or ""),
            str(event.get("sender") or event.get("sender_name") or ""),
            str(event.get("text") or event.get("message_text") or event.get("message") or ""),
            str(event.get("trace_id") or ""),
        )
        return "|".join(key_parts)

    def _has_seen_log_key(self, key: str) -> bool:
        return key in self._seen_log_key_set

    def _remember_log_key(self, key: str) -> None:
        if not key:
            return
        if len(self._seen_log_keys) == self._seen_log_keys.maxlen:
            oldest = self._seen_log_keys.popleft()
            self._seen_log_key_set.discard(oldest)
        self._seen_log_keys.append(key)
        self._seen_log_key_set.add(key)

    def _normalize_log_payload(self, event: Mapping[str, Any]) -> dict[str, Any]:
        payload = {str(key): value for key, value in event.items()}
        payload.setdefault("level", "error" if is_error_event(payload) else "info")
        payload.setdefault("message", _default_log_message(payload))
        return payload

    def _map_runtime_log_event(self, event: Mapping[str, Any]) -> dict[str, Any] | None:
        event_type = str(event.get("event_type") or "")
        if event_type in {"message_received", "message.received"}:
            return {
                "type": "message.received",
                "data": {
                    "conversation_id": _infer_conversation_id(event),
                    "sender": str(event.get("sender") or event.get("sender_name") or event.get("chat_id") or ""),
                    "text": str(event.get("text") or event.get("message_text") or event.get("message") or ""),
                    "is_group": _infer_is_group(event),
                    "source": str(event.get("source") or "runtime"),
                },
            }
        if event_type in {"message_sent", "message.sent", "message_send_unconfirmed"}:
            status = "unconfirmed" if event_type == "message_send_unconfirmed" else "sent"
            return {
                "type": "message.sent",
                "data": {
                    "conversation_id": _infer_conversation_id(event),
                    "status": status,
                    "text": str(event.get("reply_preview") or event.get("text") or event.get("message") or ""),
                    "reason_code": str(event.get("reason_code") or ""),
                },
            }
        return None


def format_sse_event(event: dict[str, Any]) -> str:
    event_id = str(event.get("id", ""))
    event_type = str(event.get("type", "message"))
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event_id}\nevent: {event_type}\ndata: {payload}\n\n"


def _default_log_message(event: Mapping[str, Any]) -> str:
    explicit_message = str(event.get("message") or "").strip()
    if explicit_message:
        return explicit_message
    event_type = str(event.get("event_type") or "").strip()
    if event_type == "message_received":
        sender = str(event.get("sender") or event.get("sender_name") or event.get("chat_id") or "unknown")
        return f"message received from {sender}"
    if event_type == "message_sent":
        return "message sent"
    if event_type == "message_send_unconfirmed":
        return "message send not confirmed"
    if event_type:
        return event_type.replace("_", " ")
    return "runtime event"


def _infer_is_group(event: Mapping[str, Any]) -> bool:
    if "is_group" in event:
        return bool(event.get("is_group"))
    chat_type = str(event.get("chat_type") or "")
    return chat_type == "group" or str(event.get("conversation_id") or "").startswith("group:")


def _infer_conversation_id(event: Mapping[str, Any]) -> str:
    conversation_id = str(event.get("conversation_id") or "").strip()
    if conversation_id:
        return conversation_id
    chat_id = str(event.get("chat_id") or "").strip()
    if not chat_id:
        return ""
    return f"{'group' if _infer_is_group(event) else 'friend'}:{chat_id}"


def _diff_environment(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    changes: list[str] = []
    tracked_keys = ["wechat_running", "ui_ready", "narrator_required"]
    for key in tracked_keys:
        if previous.get(key) != current.get(key):
            changes.append(key)
    previous_probe = previous.get("ui_probe")
    current_probe = current.get("ui_probe")
    if isinstance(previous_probe, Mapping) and isinstance(current_probe, Mapping):
        for key in ("window_ready", "window_minimized", "input_ready", "current_chat"):
            if previous_probe.get(key) != current_probe.get(key):
                changes.append(f"ui_probe.{key}")
    elif previous_probe != current_probe:
        changes.append("ui_probe")
    return changes


def _build_environment_change_message(snapshot: Mapping[str, Any], changes: list[str]) -> str:
    if not changes:
        return "wechat window environment changed"
    current_chat = ""
    ui_probe = snapshot.get("ui_probe")
    if isinstance(ui_probe, Mapping):
        current_chat = str(ui_probe.get("current_chat") or "").strip()
    chat_suffix = f" current_chat={current_chat}" if current_chat else ""
    return f"wechat window environment changed: {', '.join(changes)}{chat_suffix}"
