from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class WeChatAIIdentityMatcherTests(unittest.TestCase):
    def test_matcher_prefers_same_group_candidate_with_strong_context(self) -> None:
        from wechat_ai.identity.identity_matcher import IdentityMatcher
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity

        matcher = IdentityMatcher()
        signal = IdentityRawSignal(
            conversation_id="group:sales-war-room",
            chat_type="group",
            display_name="Alex Cc",
            sender_name="Alex Cc",
            group_name="Sales War Room",
            text="Can you send the pricing update today?",
            contexts=["Alex C said the pricing sheet will be ready after lunch."],
            captured_at="2026-04-23T12:01:00Z",
        )
        match = matcher.match(
            signal=signal,
            users=[
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                ),
                UserIdentity(
                    user_id="user_alice",
                    canonical_name="Alice Brown",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                ),
            ],
            aliases=[
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex"],
                    group_nicknames=[{"group_name": "Sales War Room", "name": "Alex C"}],
                    latest_seen_name="Alex C",
                    updated_at="2026-04-23T12:00:00Z",
                ),
                UserAlias(
                    user_id="user_alice",
                    display_names=["Alice"],
                    latest_seen_name="Alice",
                    updated_at="2026-04-23T12:00:00Z",
                ),
            ],
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.matched_user_id, "user_alex")
        self.assertGreaterEqual(match.confidence, 0.85)
        self.assertIn("alias_similarity", match.evidence)
        self.assertIn("same_group_context", match.evidence)
        self.assertIn("keyword_overlap", match.evidence)
        self.assertIn("recent_context_continuity", match.evidence)

    def test_matcher_returns_review_band_for_partial_name(self) -> None:
        from wechat_ai.identity.identity_matcher import IdentityMatcher
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity

        matcher = IdentityMatcher()
        signal = IdentityRawSignal(
            conversation_id="friend:a-chen",
            chat_type="friend",
            display_name="A. Chen",
            text="Following up on the quote.",
            contexts=["Alex said the quote is delayed until tomorrow."],
            captured_at="2026-04-23T12:01:00Z",
        )
        match = matcher.match(
            signal=signal,
            users=[
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ],
            aliases=[
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex Chen"],
                    latest_seen_name="Alex Chen",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ],
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.matched_user_id, "user_alex")
        self.assertGreaterEqual(match.confidence, 0.60)
        self.assertLess(match.confidence, 0.85)
        self.assertIn("alias_similarity", match.evidence)
        self.assertIn("recent_context_continuity", match.evidence)

    def test_matcher_keeps_low_confidence_when_signals_are_weak(self) -> None:
        from wechat_ai.identity.identity_matcher import IdentityMatcher
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity

        matcher = IdentityMatcher()
        signal = IdentityRawSignal(
            conversation_id="friend:new-person",
            chat_type="friend",
            display_name="New Person",
            text="hello there",
            contexts=["first time reaching out"],
            captured_at="2026-04-23T12:01:00Z",
        )
        match = matcher.match(
            signal=signal,
            users=[
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ],
            aliases=[
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex Chen"],
                    latest_seen_name="Alex Chen",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ],
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.matched_user_id, "user_alex")
        self.assertLess(match.confidence, 0.60)
        self.assertEqual(match.evidence, [])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIIdentityMatcherTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
