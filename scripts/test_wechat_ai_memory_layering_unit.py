from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.memory.memory_keys import (  # type: ignore  # noqa: E402
    build_conversation_memory_key,
    build_memory_lookup_keys,
    build_user_memory_key,
    choose_primary_memory_key,
)
from wechat_ai.memory.memory_store import MemoryStore  # type: ignore  # noqa: E402
from wechat_ai.storage_names import safe_storage_name  # type: ignore  # noqa: E402


class MemoryKeyLayeringTests(unittest.TestCase):
    def test_memory_key_builders_and_lookup_order_follow_layering_rules(self) -> None:
        self.assertEqual(build_user_memory_key("user_001"), "user:user_001")
        self.assertEqual(build_conversation_memory_key("group:demo"), "conversation:group:demo")
        self.assertEqual(
            build_memory_lookup_keys(
                resolved_user_id="user_001",
                conversation_id="group:demo",
                chat_id="legacy-chat",
            ),
            ["user:user_001", "conversation:group:demo", "legacy-chat"],
        )
        self.assertEqual(
            choose_primary_memory_key(
                resolved_user_id="user_001",
                conversation_id="group:demo",
                chat_id="legacy-chat",
            ),
            "user:user_001",
        )
        self.assertEqual(
            choose_primary_memory_key(
                resolved_user_id=None,
                conversation_id="group:demo",
                chat_id="legacy-chat",
            ),
            "conversation:group:demo",
        )

    def test_load_by_identity_prefers_user_then_conversation_then_chat_id(self) -> None:
        temp_dir = ROOT / ".tmp_memory_layering_unit" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        store = MemoryStore(base_dir=temp_dir)

        store.update_summary("conversation:group:demo", "Conversation summary")
        store.update_summary("legacy-chat", "Legacy summary")

        conversation_bundle = store.load_summary_bundle(
            resolved_user_id=None,
            conversation_id="group:demo",
            chat_id="legacy-chat",
        )
        self.assertEqual(conversation_bundle.lookup_key, "conversation:group:demo")
        self.assertEqual(conversation_bundle.summary_text, "Conversation summary")

        store.update_summary("user:user_001", "User summary")
        user_bundle = store.load_summary_bundle(
            resolved_user_id="user_001",
            conversation_id="group:demo",
            chat_id="legacy-chat",
        )
        self.assertEqual(user_bundle.lookup_key, "user:user_001")
        self.assertEqual(user_bundle.summary_text, "User summary")
        self.assertEqual(
            store.load_by_identity(
                resolved_user_id="user_001",
                conversation_id="group:demo",
                chat_id="legacy-chat",
            ).summary_text,
            "User summary",
        )

    def test_append_snapshot_by_identity_promotes_fallback_record_into_primary_key(self) -> None:
        temp_dir = ROOT / ".tmp_memory_layering_unit" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        store = MemoryStore(base_dir=temp_dir)

        store.update_summary("conversation:group:demo", "Conversation summary")
        store.append_snapshot("conversation:group:demo", ["older message"], captured_at="2026-04-22T10:00:00Z")

        record = store.append_snapshot_by_identity(
            resolved_user_id="user_001",
            conversation_id="group:demo",
            chat_id="legacy-chat",
            messages=["new message"],
            captured_at="2026-04-22T11:00:00Z",
        )

        self.assertEqual(record.chat_id, "user:user_001")
        self.assertEqual(record.summary_text, "Conversation summary")
        self.assertEqual([snapshot.messages for snapshot in record.recent_conversation], [["older message"], ["new message"]])

        user_path = temp_dir / f"{safe_storage_name('user:user_001', fallback='unknown_chat')}.json"
        conversation_path = temp_dir / f"{safe_storage_name('conversation:group:demo', fallback='unknown_chat')}.json"
        self.assertTrue(user_path.exists())
        self.assertTrue(conversation_path.exists())

    def test_load_compatibly_reads_legacy_json_payload_shape(self) -> None:
        temp_dir = ROOT / ".tmp_memory_layering_unit" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / f"{safe_storage_name('legacy-chat', fallback='unknown_chat')}.json"
        path.write_text(
            json.dumps(
                {
                    "chat_id": "legacy-chat",
                    "recent_conversation": [
                        {"messages": ["hi", 42, ""], "captured_at": "2026-04-22T10:00:00Z"},
                        "ignore-me",
                    ],
                    "summary_text": "Legacy summary",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        store = MemoryStore(base_dir=temp_dir)
        loaded = store.load_by_identity(chat_id="legacy-chat")

        self.assertEqual(loaded.chat_id, "legacy-chat")
        self.assertEqual(loaded.summary_text, "Legacy summary")
        self.assertEqual(len(loaded.recent_conversation), 1)
        self.assertEqual(loaded.recent_conversation[0].messages, ["hi", "42"])
        self.assertEqual(loaded.recent_conversation[0].captured_at, "2026-04-22T10:00:00Z")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MemoryKeyLayeringTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
