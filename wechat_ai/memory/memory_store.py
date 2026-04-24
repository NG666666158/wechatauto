from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..logging_utils import sanitize_text, utc_timestamp
from ..paths import MEMORY_DIR
from ..storage_names import safe_storage_name
from .conversation_memory import ConversationSnapshot
from .memory_keys import build_memory_lookup_keys, choose_primary_memory_key
from .summary_memory import SummaryMemory


@dataclass(slots=True)
class MemoryRecord:
    chat_id: str
    recent_conversation: list[ConversationSnapshot] = field(default_factory=list)
    summary_text: str = ""
    last_updated: str = ""


@dataclass(slots=True)
class MemorySummaryBundle:
    record: MemoryRecord
    lookup_key: str
    summary_text: str


class MemoryStore:
    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        max_snapshots: int = 20,
        max_messages_per_snapshot: int = 8,
        max_chars_per_message: int = 280,
        max_summary_chars: int = 2000,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else MEMORY_DIR
        self.max_snapshots = max_snapshots
        self.max_messages_per_snapshot = max_messages_per_snapshot
        self.max_chars_per_message = max_chars_per_message
        self.max_summary_chars = max_summary_chars

    def load(self, chat_id: str) -> MemoryRecord:
        path = self._path_for_chat(chat_id)
        if not path.exists():
            return MemoryRecord(chat_id=chat_id)
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return self._record_from_payload(payload, default_chat_id=chat_id)

    def load_by_identity(
        self,
        *,
        resolved_user_id: str | None = None,
        conversation_id: str | None = None,
        chat_id: str | None = None,
    ) -> MemoryRecord:
        primary_key = choose_primary_memory_key(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        existing_key = self._find_existing_identity_key(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        if existing_key is None:
            return MemoryRecord(chat_id=primary_key)
        return self.load(existing_key)

    def save(self, record: MemoryRecord) -> MemoryRecord:
        payload = asdict(record)
        path = self._path_for_chat(record.chat_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return record

    def update_summary(self, chat_id: str, summary_text: str) -> MemoryRecord:
        record = self.load(chat_id)
        record.summary_text = sanitize_text(summary_text, max_chars=self.max_summary_chars)
        record.last_updated = utc_timestamp()
        return self.save(record)

    def append_snapshot(self, chat_id: str, messages: list[str], *, captured_at: str | None = None) -> MemoryRecord:
        record = self.load(chat_id)
        return self._append_snapshot_to_record(record, messages=messages, captured_at=captured_at)

    def append_snapshot_by_identity(
        self,
        *,
        resolved_user_id: str | None = None,
        conversation_id: str | None = None,
        chat_id: str | None = None,
        messages: list[str],
        captured_at: str | None = None,
    ) -> MemoryRecord:
        primary_key = choose_primary_memory_key(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        loaded = self.load_by_identity(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        if loaded.chat_id != primary_key:
            loaded = MemoryRecord(
                chat_id=primary_key,
                recent_conversation=list(loaded.recent_conversation),
                summary_text=loaded.summary_text,
                last_updated=loaded.last_updated,
            )
        return self._append_snapshot_to_record(loaded, messages=messages, captured_at=captured_at)

    def load_summary_text(self, chat_id: str) -> str:
        return self.load(chat_id).summary_text.strip()

    def load_summary_bundle(
        self,
        *,
        resolved_user_id: str | None = None,
        conversation_id: str | None = None,
        chat_id: str | None = None,
    ) -> MemorySummaryBundle:
        record = self.load_by_identity(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        lookup_key = self._find_existing_identity_key(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        ) or choose_primary_memory_key(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        )
        return MemorySummaryBundle(record=record, lookup_key=lookup_key, summary_text=record.summary_text.strip())

    def _path_for_chat(self, chat_id: str) -> Path:
        safe_name = safe_storage_name(chat_id, fallback="unknown_chat")
        return self.base_dir / f"{safe_name}.json"

    def _record_from_payload(self, payload: object, *, default_chat_id: str) -> MemoryRecord:
        if not isinstance(payload, dict):
            return MemoryRecord(chat_id=default_chat_id)
        snapshots = [
            ConversationSnapshot(
                messages=[str(item) for item in snapshot.get("messages", []) if str(item).strip()],
                captured_at=str(snapshot.get("captured_at", "")),
            )
            for snapshot in payload.get("recent_conversation", [])
            if isinstance(snapshot, dict)
        ]
        return MemoryRecord(
            chat_id=str(payload.get("chat_id", default_chat_id)),
            recent_conversation=snapshots,
            summary_text=str(payload.get("summary_text", "")),
            last_updated=str(payload.get("last_updated", "")),
        )

    def _append_snapshot_to_record(
        self,
        record: MemoryRecord,
        *,
        messages: list[str],
        captured_at: str | None = None,
    ) -> MemoryRecord:
        cleaned = [
            sanitize_text(message, max_chars=self.max_chars_per_message)
            for message in messages
            if str(message).strip()
        ]
        if self.max_messages_per_snapshot > 0:
            cleaned = cleaned[-self.max_messages_per_snapshot :]
        if cleaned:
            timestamp = captured_at or utc_timestamp()
            record.recent_conversation.append(ConversationSnapshot(messages=cleaned, captured_at=timestamp))
            if self.max_snapshots > 0:
                record.recent_conversation = record.recent_conversation[-self.max_snapshots :]
            record.last_updated = timestamp
            self.save(record)
        return record

    def _find_existing_identity_key(
        self,
        *,
        resolved_user_id: str | None = None,
        conversation_id: str | None = None,
        chat_id: str | None = None,
    ) -> str | None:
        for key in build_memory_lookup_keys(
            resolved_user_id=resolved_user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
        ):
            if self._path_for_chat(key).exists():
                return key
        return None
