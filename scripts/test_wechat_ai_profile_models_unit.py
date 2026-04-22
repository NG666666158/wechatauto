from __future__ import annotations

import json
import sys
import unittest
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.profile.agent_profile import AgentProfile  # type: ignore  # noqa: E402
from wechat_ai.profile.user_profile import UserProfile  # type: ignore  # noqa: E402


class UserProfileTests(unittest.TestCase):
    def test_default_construction_uses_explicit_empty_collections(self) -> None:
        profile = UserProfile(user_id="friend_demo")

        self.assertEqual(profile.user_id, "friend_demo")
        self.assertEqual(profile.display_name, "")
        self.assertEqual(profile.tags, [])
        self.assertEqual(profile.notes, [])
        self.assertEqual(profile.preferences, {})

    def test_default_collections_are_not_shared_between_instances(self) -> None:
        first = UserProfile(user_id="first")
        second = UserProfile(user_id="second")

        first.tags.append("vip")
        first.notes.append("prefers short replies")
        first.preferences["tone"] = "direct"

        self.assertEqual(second.tags, [])
        self.assertEqual(second.notes, [])
        self.assertEqual(second.preferences, {})

    def test_asdict_round_trip_preserves_serializable_shape(self) -> None:
        original = UserProfile(
            user_id="friend_demo",
            display_name="Demo Friend",
            tags=["vip", "english"],
            notes=["Met at the expo."],
            preferences={"tone": "warm", "length": "short"},
        )

        payload = asdict(original)
        restored = UserProfile(**json.loads(json.dumps(payload)))

        self.assertEqual(restored, original)


class AgentProfileTests(unittest.TestCase):
    def test_default_construction_uses_explicit_empty_collections(self) -> None:
        profile = AgentProfile(agent_id="default_assistant")

        self.assertEqual(profile.agent_id, "default_assistant")
        self.assertEqual(profile.display_name, "")
        self.assertEqual(profile.style_rules, [])
        self.assertEqual(profile.goals, [])
        self.assertEqual(profile.forbidden_rules, [])
        self.assertEqual(profile.notes, [])

    def test_default_collections_are_not_shared_between_instances(self) -> None:
        first = AgentProfile(agent_id="first")
        second = AgentProfile(agent_id="second")

        first.style_rules.append("Keep replies concise.")
        first.goals.append("Help users unblock quickly.")
        first.forbidden_rules.append("Do not invent facts.")
        first.notes.append("Escalate billing issues.")

        self.assertEqual(second.style_rules, [])
        self.assertEqual(second.goals, [])
        self.assertEqual(second.forbidden_rules, [])
        self.assertEqual(second.notes, [])

    def test_asdict_round_trip_preserves_serializable_shape(self) -> None:
        original = AgentProfile(
            agent_id="default_assistant",
            display_name="Helpful Assistant",
            style_rules=["Be clear.", "Be calm."],
            goals=["Resolve the user's question."],
            forbidden_rules=["Do not leak secrets."],
            notes=["Use profile context when available."],
        )

        payload = asdict(original)
        restored = AgentProfile(**json.loads(json.dumps(payload)))

        self.assertEqual(restored, original)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(UserProfileTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(AgentProfileTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
