from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.models import Message  # type: ignore  # noqa: E402
from wechat_ai.orchestration.reply_pipeline import ReplyPipeline, ScenePrompts  # type: ignore  # noqa: E402


class SelfIdentityIntegrationTests(unittest.TestCase):
    def test_pipeline_passes_self_identity_to_engine_and_prompt_preview(self) -> None:
        class FakeReplyEngine:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []
                self.prompt_builder = types.SimpleNamespace(
                    debug_preview=lambda **kwargs: f"preview::{getattr(kwargs['self_identity_profile'], 'relationship', '')}"
                )

            def generate_friend_reply(self, latest_message: str, contexts: list[str], **kwargs: object) -> str:
                self.calls.append(kwargs)
                return "ok"

        class FakeResolver:
            def resolve(self, **kwargs):
                return types.SimpleNamespace(
                    relationship="teacher",
                    summary="事实: 我是 2023 级学生",
                    identity_facts=["我是 2023 级学生"],
                )

        logged_events: list[str] = []

        class FakeLogger:
            def log_event(self, event_type: str, **fields: object) -> None:
                del fields
                logged_events.append(event_type)

        engine = FakeReplyEngine()
        pipeline = ReplyPipeline(
            provider=object(),
            prompts=ScenePrompts(friend_system_prompt="friend", group_system_prompt="group"),
            reply_engine=engine,
            self_identity_resolver=FakeResolver(),
            event_logger=FakeLogger(),
        )

        reply = pipeline.generate_reply(
            Message(chat_id="alice", chat_type="friend", sender_name="Alice", text="你好", relationship_to_me="teacher")
        )

        self.assertEqual(reply, "ok")
        self.assertEqual(engine.calls[0]["self_identity_profile"].relationship, "teacher")
        self.assertIn("self_identity_resolved", logged_events)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfIdentityIntegrationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
