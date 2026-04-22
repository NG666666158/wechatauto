from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..logging_utils import sanitize_text, utc_timestamp
from ..paths import MEMORY_DIR
from .conversation_memory import ConversationSnapshot
from .summary_memory import SummaryMemory


@dataclass(slots=True)
class MemoryRecord:
    chat_id: str
    recent_conversation: list[ConversationSnapshot] = field(default_factory=list)
    summary_text: str = ""
    last_updated: str = ""


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
        snapshots = [
            ConversationSnapshot(
                messages=[str(item) for item in snapshot.get("messages", []) if str(item).strip()],
                captured_at=str(snapshot.get("captured_at", "")),
            )
            for snapshot in payload.get("recent_conversation", [])
            if isinstance(snapshot, dict)
        ]
        return MemoryRecord(
            chat_id=str(payload.get("chat_id", chat_id)),
            recent_conversation=snapshots,
            summary_text=str(payload.get("summary_text", "")),
            last_updated=str(payload.get("last_updated", "")),
        )

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
        cleaned = [
            sanitize_text(message, max_chars=self.max_chars_per_message)
            for message in messages
            if str(message).strip()
        ]
        if self.max_messages_per_snapshot > 0:
            cleaned = cleaned[-self.max_messages_per_snapshot :]
        record = self.load(chat_id)
        if cleaned:
            record.recent_conversation.append(
                ConversationSnapshot(messages=cleaned, captured_at=captured_at or utc_timestamp())
            )
            if self.max_snapshots > 0:
                record.recent_conversation = record.recent_conversation[-self.max_snapshots :]
            record.last_updated = captured_at or utc_timestamp()
            self.save(record)
        return record

    def load_summary_text(self, chat_id: str) -> str:
        return self.load(chat_id).summary_text.strip()

    def _path_for_chat(self, chat_id: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", chat_id.strip()) or "unknown_chat"
        return self.base_dir / f"{safe_name}.json"
