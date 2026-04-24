from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.models import Message  # type: ignore  # noqa: E402
from wechat_ai.orchestration.reply_pipeline import ReplyPipeline, ScenePrompts  # type: ignore  # noqa: E402


class WeChatAIIdentityIntegrationTests(unittest.TestCase):
    def test_message_accepts_identity_resolution_fields(self) -> None:
        message = Message(
            chat_id="room",
            chat_type="group",
            sender_name="张三",
            text="hello",
            resolved_user_id="user_000001",
            conversation_id="group:room",
            participant_display_name="张三",
            relationship_to_me="朋友",
            current_intent="闲聊",
            identity_confidence=0.99,
            identity_status="resolved",
            identity_evidence=["alias_exact_match"],
        )

        self.assertEqual(message.resolved_user_id, "user_000001")
        self.assertEqual(message.identity_status, "resolved")
        self.assertEqual(message.identity_evidence, ["alias_exact_match"])

    def test_reply_pipeline_loads_profile_by_resolved_user_id_first(self) -> None:
        loaded_user_ids: list[str] = []

        class FakeProfileStore:
            def load_user_profile(self, user_id: str):
                loaded_user_ids.append(user_id)
                return types.SimpleNamespace(user_id=user_id)

            def load_agent_profile(self, agent_id: str):
                return types.SimpleNamespace(agent_id=agent_id)

        class FakeReplyEngine:
            def __init__(self) -> None:
                self.prompt_builder = types.SimpleNamespace(debug_preview=lambda **kwargs: "preview")

            def generate_group_reply(self, latest_message: str, contexts: list[str], **kwargs: object) -> str:
                return "reply"

        pipeline = ReplyPipeline(
            provider=object(),
            prompts=ScenePrompts(friend_system_prompt="friend", group_system_prompt="group"),
            profile_store=FakeProfileStore(),
            reply_engine=FakeReplyEngine(),
        )

        pipeline.generate_reply(
            Message(
                chat_id="group-room",
                chat_type="group",
                sender_name="张三",
                text="@bot hi",
                resolved_user_id="user_000001",
            )
        )

        self.assertEqual(loaded_user_ids, ["user_000001"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIIdentityIntegrationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
