from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from wechat_ai.logging_utils import utc_timestamp


_WRITE_LOCK = threading.Lock()


class ConversationStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def list_records(self) -> dict[str, Any]:
        return self._load()

    def get_record(self, conversation_id: str) -> dict[str, Any]:
        normalized_id = str(conversation_id).strip()
        payload = self._load()
        record = payload.get(normalized_id)
        if isinstance(record, dict):
            return record
        return {
            "title": conversation_title(normalized_id),
            "is_group": normalized_id.startswith("group:"),
            "unread_count": 0,
            "messages": [],
        }

    def append_message(
        self,
        conversation_id: str,
        *,
        sender: str,
        text: str,
        direction: str = "incoming",
        sent_at: str | None = None,
        title: str = "",
        is_group: bool | None = None,
        delivery_status: str = "sent",
    ) -> dict[str, Any]:
        normalized_id = str(conversation_id).strip()
        safe_direction = direction if direction in {"incoming", "outgoing"} else "incoming"
        safe_delivery_status = str(delivery_status).strip() or "sent"
        message = {
            "message_id": f"msg_{uuid4().hex}",
            "conversation_id": normalized_id,
            "sender": str(sender).strip() or ("assistant" if safe_direction == "outgoing" else "unknown"),
            "text": str(text),
            "direction": safe_direction,
            "sent_at": sent_at or utc_timestamp(),
        }
        if safe_direction == "outgoing" and safe_delivery_status != "sent":
            message["delivery_status"] = safe_delivery_status

        with _WRITE_LOCK:
            payload = self._load()
            record = payload.get(normalized_id)
            if not isinstance(record, dict):
                record = {
                    "title": title or str(sender).strip() or conversation_title(normalized_id),
                    "is_group": normalized_id.startswith("group:"),
                    "unread_count": 0,
                    "messages": [],
                }
            messages = record.get("messages")
            if not isinstance(messages, list):
                messages = []
            messages.append(message)
            record["messages"] = messages[-100:]
            record["title"] = str(record.get("title", "")).strip() or title or str(sender).strip() or conversation_title(normalized_id)
            record["is_group"] = bool(is_group) if is_group is not None else bool(record.get("is_group", normalized_id.startswith("group:")))
            record["updated_at"] = message["sent_at"]
            if safe_direction == "incoming":
                record["unread_count"] = int(record.get("unread_count", 0)) + 1
            payload[normalized_id] = record
            self._save(payload)
        return message

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save(self, payload: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def conversation_title(conversation_id: str) -> str:
    normalized = str(conversation_id).strip()
    if ":" in normalized:
        return normalized.split(":", 1)[1]
    return normalized
