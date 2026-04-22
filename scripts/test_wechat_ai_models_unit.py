from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class WeChatAIModelsTests(unittest.TestCase):
    def test_message_defaults_timestamp_and_context(self) -> None:
        from wechat_ai import Message

        message = Message(
            chat_id="chat-1",
            chat_type="friend",
            sender_name="Alice",
            text="hello",
        )

        self.assertEqual(message.chat_id, "chat-1")
        self.assertEqual(message.chat_type, "friend")
        self.assertEqual(message.sender_name, "Alice")
        self.assertEqual(message.text, "hello")
        self.assertIsNone(message.timestamp)
        self.assertEqual(message.context, [])

    def test_message_uses_independent_default_context_lists(self) -> None:
        from wechat_ai import Message

        first = Message(chat_id="chat-1", chat_type="friend", sender_name="Alice", text="hello")
        second = Message(chat_id="chat-2", chat_type="friend", sender_name="Bob", text="hi")

        first.context.append("prior message")

        self.assertEqual(first.context, ["prior message"])
        self.assertEqual(second.context, [])

    def test_retrieved_chunk_defaults_metadata(self) -> None:
        from wechat_ai import RetrievedChunk

        chunk = RetrievedChunk(text="knowledge", score=0.9)

        self.assertEqual(chunk.text, "knowledge")
        self.assertEqual(chunk.score, 0.9)
        self.assertEqual(chunk.metadata, {})

    def test_retrieved_chunk_uses_independent_default_metadata(self) -> None:
        from wechat_ai import RetrievedChunk

        first = RetrievedChunk(text="knowledge", score=0.9)
        second = RetrievedChunk(text="other", score=0.7)

        first.metadata["source"] = "notes"

        self.assertEqual(first.metadata, {"source": "notes"})
        self.assertEqual(second.metadata, {})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIModelsTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
