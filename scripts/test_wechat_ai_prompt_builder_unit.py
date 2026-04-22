from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.orchestration.prompt_builder import PromptBuilder  # type: ignore  # noqa: E402
from wechat_ai.profile.agent_profile import AgentProfile  # type: ignore  # noqa: E402
from wechat_ai.profile.user_profile import UserProfile  # type: ignore  # noqa: E402
from wechat_ai.reply_engine import ReplyEngine, ScenePrompts  # type: ignore  # noqa: E402


class PromptBuilderTests(unittest.TestCase):
    def test_render_prompt_includes_sections_in_expected_order(self) -> None:
        builder = PromptBuilder(context_limit=2)

        prompt = builder.render_prompt(
            scene="friend",
            latest_message="Can you summarize the plan?",
            contexts=["old context", "new context", "latest context"],
            agent_profile=AgentProfile(
                agent_id="assistant",
                display_name="Helper",
                style_rules=["Warm", "Concise"],
                goals=["Keep momentum"],
                forbidden_rules=["Don't fabricate"],
                notes=["Prefer direct answers"],
            ),
            user_profile=UserProfile(
                user_id="alice",
                display_name="Alice",
                tags=["vip", "teammate"],
                notes=["Prefers concrete next steps"],
                preferences={"tone": "friendly", "length": "short"},
            ),
            knowledge_chunks=["Project plan approved", "Tests should be focused"],
            memory_summary="Alice usually wants a short answer first.",
        )

        expected_headers = [
            "## Agent Profile Summary",
            "## User Profile Summary",
            "## Recent Conversation Context",
            "## Retrieved Knowledge",
            "## Conversation Memory Summary",
            "## Current Reply Task",
        ]
        positions = [prompt.index(header) for header in expected_headers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Helper", prompt)
        self.assertIn("Alice", prompt)
        self.assertIn("1. new context", prompt)
        self.assertIn("2. latest context", prompt)
        self.assertNotIn("old context", prompt)
        self.assertIn("Project plan approved", prompt)
        self.assertIn("Alice usually wants a short answer first.", prompt)
        self.assertIn("Scene: friend", prompt)
        self.assertIn("Latest message: Can you summarize the plan?", prompt)

    def test_debug_preview_matches_rendered_prompt(self) -> None:
        builder = PromptBuilder()

        prompt = builder.render_prompt(
            scene="group",
            latest_message="@me please reply",
            contexts=[],
        )

        preview = builder.debug_preview(
            scene="group",
            latest_message="@me please reply",
            contexts=[],
        )

        self.assertEqual(preview, prompt)
        self.assertIn("(no retrieved knowledge)", preview)
        self.assertNotIn("## Conversation Memory Summary", preview)


class ReplyEnginePromptBuilderIntegrationTests(unittest.TestCase):
    def test_reply_engine_uses_prompt_builder_for_user_prompt(self) -> None:
        captured: dict[str, str | None] = {}

        class FakeProvider:
            def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
                captured["system_prompt"] = system_prompt
                captured["user_prompt"] = user_prompt
                captured["model"] = model
                return "ok"

        class FakePromptBuilder:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def render_prompt(
                self,
                *,
                scene: str,
                latest_message: str,
                contexts: list[str],
                agent_profile=None,
                user_profile=None,
                knowledge_chunks=None,
                memory_summary=None,
            ) -> str:
                self.calls.append(
                    {
                        "scene": scene,
                        "latest_message": latest_message,
                        "contexts": list(contexts),
                        "agent_profile": agent_profile,
                        "user_profile": user_profile,
                        "knowledge_chunks": knowledge_chunks,
                        "memory_summary": memory_summary,
                    }
                )
                return "builder-output"

        prompt_builder = FakePromptBuilder()
        engine = ReplyEngine(
            provider=FakeProvider(),
            prompts=ScenePrompts(
                friend_system_prompt="friend-system",
                group_system_prompt="group-system",
            ),
            prompt_builder=prompt_builder,
            model="MiniMax-M2.5",
        )

        reply = engine.generate_friend_reply(
            latest_message="hello",
            contexts=["ctx-1", "ctx-2"],
        )

        self.assertEqual(reply, "ok")
        self.assertEqual(captured["system_prompt"], "friend-system")
        self.assertEqual(captured["user_prompt"], "builder-output")
        self.assertEqual(captured["model"], "MiniMax-M2.5")
        self.assertEqual(
            prompt_builder.calls,
            [
                {
                    "scene": "friend",
                    "latest_message": "hello",
                    "contexts": ["ctx-1", "ctx-2"],
                    "agent_profile": None,
                    "user_profile": None,
                    "knowledge_chunks": None,
                    "memory_summary": None,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
