from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ReplySchedulerTests(unittest.TestCase):
    def test_same_session_messages_merge_within_window(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(merge_window_seconds=5.0)

        self.assertEqual(
            scheduler.add_message(
                session_name="Alice",
                chat_type="friend",
                text="hello",
                contexts=["ctx-1"],
                sender_name="Alice",
                now=10.0,
            ),
            [],
        )
        self.assertEqual(
            scheduler.add_message(
                session_name="Alice",
                chat_type="friend",
                text="second",
                contexts=["ctx-2"],
                sender_name="Alice",
                now=12.0,
            ),
            [],
        )

        ready = scheduler.drain_ready(now=17.0)

        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].session_name, "Alice")
        self.assertEqual(ready[0].chat_type, "friend")
        self.assertEqual(ready[0].sender_name, "Alice")
        self.assertEqual(ready[0].messages, ["hello", "second"])
        self.assertEqual(ready[0].contexts, ["ctx-1", "ctx-2"])
        self.assertEqual(ready[0].first_seen_at, 10.0)
        self.assertEqual(ready[0].last_seen_at, 12.0)
        self.assertEqual(ready[0].deadline, 17.0)

    def test_different_sessions_keep_independent_pending_batches(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(merge_window_seconds=5.0)

        scheduler.add_message("Alice", "friend", "from alice", [], "Alice", now=10.0)
        scheduler.add_message("Bob", "friend", "from bob", [], "Bob", now=12.0)

        ready = scheduler.drain_ready(now=15.0)

        self.assertEqual([batch.session_name for batch in ready], ["Alice"])
        self.assertEqual(ready[0].messages, ["from alice"])

        remaining = scheduler.flush_all(reason="shutdown")
        self.assertEqual([batch.session_name for batch in remaining], ["Bob"])
        self.assertEqual(remaining[0].messages, ["from bob"])

    def test_deadline_drain_returns_ready_batch_once(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(merge_window_seconds=3.0)
        scheduler.add_message("Alice", "friend", "hello", [], "Alice", now=10.0)

        self.assertEqual(scheduler.drain_ready(now=12.9), [])

        ready = scheduler.drain_ready(now=13.0)
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].messages, ["hello"])
        self.assertEqual(scheduler.drain_ready(now=99.0), [])

    def test_max_batch_size_becomes_ready_immediately(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(merge_window_seconds=30.0, max_messages_per_batch=2)

        self.assertEqual(scheduler.add_message("Alice", "friend", "one", [], "Alice", now=10.0), [])
        ready = scheduler.add_message("Alice", "friend", "two", [], "Alice", now=11.0)

        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].session_name, "Alice")
        self.assertEqual(ready[0].messages, ["one", "two"])
        self.assertEqual(scheduler.drain_ready(now=12.0), [])

    def test_flush_all_returns_all_pending_batches_and_clears_them(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(merge_window_seconds=30.0)
        scheduler.add_message("Alice", "friend", "one", [], "Alice", now=10.0)
        scheduler.add_message("Room", "group", "@me hi", ["room ctx"], "Bob", now=11.0)

        ready = scheduler.flush_all(reason="shutdown")

        self.assertEqual([batch.session_name for batch in ready], ["Alice", "Room"])
        self.assertEqual(ready[0].messages, ["one"])
        self.assertEqual(ready[1].messages, ["@me hi"])
        self.assertEqual(scheduler.flush_all(reason="again"), [])

    def test_min_reply_interval_delays_session_until_interval_elapsed(self) -> None:
        from wechat_ai.reply_scheduler import ReplyScheduler

        scheduler = ReplyScheduler(
            merge_window_seconds=2.0,
            min_reply_interval_seconds=10.0,
        )
        scheduler.add_message("Alice", "friend", "first", [], "Alice", now=0.0)
        first_ready = scheduler.drain_ready(now=2.0)
        self.assertEqual(len(first_ready), 1)

        scheduler.add_message("Alice", "friend", "second", [], "Alice", now=3.0)

        self.assertEqual(scheduler.drain_ready(now=5.0), [])
        delayed_ready = scheduler.drain_ready(now=12.0)

        self.assertEqual(len(delayed_ready), 1)
        self.assertEqual(delayed_ready[0].messages, ["second"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReplySchedulerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
