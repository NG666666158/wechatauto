from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class MessageEventQueueTests(unittest.TestCase):
    def event(
        self,
        session_name: str,
        text: str,
        signature: str,
        captured_at: float,
        contexts: list[str] | None = None,
        chat_type: str = "friend",
        sender_name: str = "Alice",
        source: str = "unread",
    ):
        from wechat_ai.message_queue import IncomingMessageEvent

        return IncomingMessageEvent(
            session_name=session_name,
            chat_type=chat_type,
            text=text,
            contexts=list(contexts or []),
            sender_name=sender_name,
            source=source,
            signature=signature,
            captured_at=captured_at,
        )

    def test_same_session_ready_events_merge_with_latest_contexts(self) -> None:
        from wechat_ai.message_queue import MessageEventQueue

        queue = MessageEventQueue()
        queue.enqueue_many(
            [
                self.event("Alice", "first", "sig-1", 1.0, contexts=["old"]),
                self.event("Alice", "second", "sig-2", 2.0, contexts=["new"]),
            ]
        )

        batches = queue.drain_ready(now=3.0)

        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertEqual(batch.session_name, "Alice")
        self.assertEqual(batch.text, "first\nsecond")
        self.assertEqual(batch.contexts, ["new"])
        self.assertEqual([event.signature for event in batch.events], ["sig-1", "sig-2"])

    def test_different_sessions_are_drained_independently(self) -> None:
        from wechat_ai.message_queue import MessageEventQueue

        queue = MessageEventQueue()
        queue.enqueue_many(
            [
                self.event("Alice", "hello", "sig-a", 1.0),
                self.event("Bob", "hi", "sig-b", 1.5, sender_name="Bob"),
            ]
        )

        batches = queue.drain_ready(now=2.0)

        self.assertEqual([batch.session_name for batch in batches], ["Alice", "Bob"])
        self.assertEqual([batch.text for batch in batches], ["hello", "hi"])

    def test_duplicate_signature_is_not_enqueued_while_seen(self) -> None:
        from wechat_ai.message_queue import MessageEventQueue

        queue = MessageEventQueue(seen_ttl_seconds=60)
        queue.enqueue_many(
            [
                self.event("Alice", "original", "same-sig", 1.0),
                self.event("Alice", "duplicate", "same-sig", 2.0),
            ]
        )

        batches = queue.drain_ready(now=3.0)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].text, "original")
        self.assertEqual([event.signature for event in batches[0].events], ["same-sig"])

    def test_seen_ttl_allows_signature_to_be_enqueued_again(self) -> None:
        from wechat_ai.message_queue import MessageEventQueue

        queue = MessageEventQueue(seen_ttl_seconds=5)
        queue.enqueue_many([self.event("Alice", "original", "sig-ttl", 1.0)])
        queue.drain_ready(now=2.0)

        queue.enqueue_many([self.event("Alice", "after ttl", "sig-ttl", 7.1)])
        batches = queue.drain_ready(now=8.0)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].text, "after ttl")

    def test_seen_limit_prunes_old_signatures(self) -> None:
        from wechat_ai.message_queue import MessageEventQueue

        queue = MessageEventQueue(seen_limit=2, seen_ttl_seconds=999)
        queue.enqueue_many(
            [
                self.event("Alice", "one", "sig-1", 1.0),
                self.event("Alice", "two", "sig-2", 2.0),
                self.event("Alice", "three", "sig-3", 3.0),
            ]
        )
        queue.flush_all()

        queue.enqueue_many([self.event("Alice", "one again", "sig-1", 4.0)])
        batches = queue.drain_ready(now=5.0)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].text, "one again")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MessageEventQueueTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
