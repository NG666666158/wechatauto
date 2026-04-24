from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


class WeChatAIIdentityTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / "identity_tests" / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        return path

    def test_repository_round_trips_identity_documents(self) -> None:
        from wechat_ai.identity.identity_models import IdentityCandidate, UserAlias, UserIdentity
        from wechat_ai.identity.identity_repository import IdentityRepository

        repo = IdentityRepository(base_dir=self.make_temp_dir())
        user = UserIdentity(
            user_id="user_000001",
            canonical_name="张三",
            user_type="客户",
            relationship_to_me="商家客户",
            status="confirmed",
            created_at="2026-04-23T12:00:00Z",
            updated_at="2026-04-23T12:00:00Z",
        )
        alias = UserAlias(
            user_id="user_000001",
            display_names=["张三"],
            remarks=["张总客户"],
            group_nicknames=[{"group_name": "供应商群", "name": "张总"}],
            latest_seen_name="张三",
            updated_at="2026-04-23T12:00:00Z",
        )

        repo.save_users([user])
        repo.save_aliases([alias])
        repo.save_candidates(
            [
                IdentityCandidate(
                    candidate_id="candidate_000001",
                    incoming_name="Alex Cc",
                    matched_user_id="user_000001",
                    confidence=0.74,
                    evidence=["alias_similarity", "recent_context_continuity"],
                )
            ]
        )

        self.assertEqual(repo.load_users(), [user])
        self.assertEqual(repo.load_aliases(), [alias])
        self.assertEqual(repo.load_candidates()[0].candidate_id, "candidate_000001")
        self.assertEqual(repo.load_candidates()[0].status, "pending_review")

    def test_alias_manager_resolves_friend_and_group_aliases(self) -> None:
        from wechat_ai.identity.alias_manager import AliasManager
        from wechat_ai.identity.identity_models import UserAlias
        from wechat_ai.identity.identity_repository import IdentityRepository

        repo = IdentityRepository(base_dir=self.make_temp_dir())
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_000001",
                    display_names=["张三"],
                    remarks=["张总客户"],
                    group_nicknames=[{"group_name": "供应商群", "name": "张总"}],
                    latest_seen_name="张三",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        manager = AliasManager(repo)

        self.assertEqual(manager.resolve_alias(display_name="张三"), "user_000001")
        self.assertEqual(manager.resolve_alias(display_name="张总客户"), "user_000001")
        self.assertEqual(
            manager.resolve_alias(display_name="张总", group_name="供应商群"),
            "user_000001",
        )

    def test_resolver_returns_alias_hit_and_logs_event(self) -> None:
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias
        from wechat_ai.identity.identity_repository import IdentityRepository
        from wechat_ai.identity.identity_resolver import IdentityResolver

        events: list[dict[str, object]] = []
        repo = IdentityRepository(base_dir=self.make_temp_dir())
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_000001",
                    display_names=["张三"],
                    latest_seen_name="张三",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        resolver = IdentityResolver(
            repository=repo,
            event_logger=type("Logger", (), {"log_event": lambda self, event_type, **fields: events.append({"event_type": event_type, **fields})})(),
        )

        result = resolver.resolve(
            IdentityRawSignal(
                conversation_id="friend:张三",
                chat_type="friend",
                display_name="张三",
                text="你好",
                contexts=[],
                captured_at="2026-04-23T12:01:00Z",
            )
        )

        self.assertEqual(result.resolved_user_id, "user_000001")
        self.assertEqual(result.identity_status, "resolved")
        self.assertGreaterEqual(result.identity_confidence, 0.99)
        self.assertIn("alias_exact_match", result.evidence)
        self.assertEqual([event["event_type"] for event in events], ["identity_resolve_started", "identity_alias_hit"])

    def test_resolver_creates_reusable_draft_when_alias_misses(self) -> None:
        from wechat_ai.identity.identity_models import IdentityRawSignal
        from wechat_ai.identity.identity_repository import IdentityRepository
        from wechat_ai.identity.identity_resolver import IdentityResolver

        events: list[dict[str, object]] = []
        repo = IdentityRepository(base_dir=self.make_temp_dir())
        resolver = IdentityResolver(
            repository=repo,
            event_logger=type("Logger", (), {"log_event": lambda self, event_type, **fields: events.append({"event_type": event_type, **fields})})(),
        )

        signal = IdentityRawSignal(
            conversation_id="friend:新客户",
            chat_type="friend",
            display_name="新客户",
            text="老板，订单什么时候发货？",
            contexts=[],
            captured_at="2026-04-23T12:01:00Z",
        )
        first = resolver.resolve(signal)
        second = resolver.resolve(signal)

        self.assertEqual(first.identity_status, "draft")
        self.assertEqual(second.identity_status, "draft")
        self.assertEqual(first.draft_user_id, second.draft_user_id)
        self.assertIsNone(first.resolved_user_id)
        self.assertEqual(len(repo.load_draft_users()), 1)
        self.assertEqual(repo.load_draft_users()[0].proposed_name, "新客户")
        self.assertIn("message_contains_order_keywords", repo.load_draft_users()[0].source_signals)
        self.assertIn("identity_draft_created", [event["event_type"] for event in events])

    def test_resolver_auto_merges_high_confidence_match_and_updates_alias(self) -> None:
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity
        from wechat_ai.identity.identity_repository import IdentityRepository
        from wechat_ai.identity.identity_resolver import IdentityResolver

        events: list[dict[str, object]] = []
        repo = IdentityRepository(base_dir=self.make_temp_dir())
        repo.save_users(
            [
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex"],
                    group_nicknames=[{"group_name": "Sales War Room", "name": "Alex C"}],
                    latest_seen_name="Alex C",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        resolver = IdentityResolver(
            repository=repo,
            event_logger=type("Logger", (), {"log_event": lambda self, event_type, **fields: events.append({"event_type": event_type, **fields})})(),
        )

        result = resolver.resolve(
            IdentityRawSignal(
                conversation_id="group:sales-war-room",
                chat_type="group",
                display_name="Alex Cc",
                sender_name="Alex Cc",
                text="Can you send the pricing update today?",
                contexts=["Alex C said the pricing sheet will be ready after lunch."],
                group_name="Sales War Room",
                captured_at="2026-04-23T12:01:00Z",
            )
        )

        aliases = repo.load_aliases()

        self.assertEqual(result.resolved_user_id, "user_alex")
        self.assertEqual(result.identity_status, "resolved")
        self.assertGreaterEqual(result.identity_confidence, 0.85)
        self.assertIn({"group_name": "Sales War Room", "name": "Alex Cc"}, aliases[0].group_nicknames)
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "identity_resolve_started",
                "identity_auto_merged",
                "identity_alias_updated",
            ],
        )

    def test_resolver_creates_review_candidate_for_medium_confidence_match(self) -> None:
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity
        from wechat_ai.identity.identity_repository import IdentityRepository
        from wechat_ai.identity.identity_resolver import IdentityResolver

        events: list[dict[str, object]] = []
        repo = IdentityRepository(base_dir=self.make_temp_dir())
        repo.save_users(
            [
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex Chen"],
                    latest_seen_name="Alex Chen",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        resolver = IdentityResolver(
            repository=repo,
            event_logger=type("Logger", (), {"log_event": lambda self, event_type, **fields: events.append({"event_type": event_type, **fields})})(),
        )

        result = resolver.resolve(
            IdentityRawSignal(
                conversation_id="friend:a-chen",
                chat_type="friend",
                display_name="A. Chen",
                text="Following up on the quote.",
                contexts=["Alex said the quote is delayed until tomorrow."],
                captured_at="2026-04-23T12:01:00Z",
            )
        )

        candidates = repo.load_candidates()

        self.assertEqual(result.identity_status, "review")
        self.assertIsNone(result.resolved_user_id)
        self.assertIsNone(result.draft_user_id)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].matched_user_id, "user_alex")
        self.assertGreaterEqual(candidates[0].confidence, 0.60)
        self.assertLess(candidates[0].confidence, 0.85)
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "identity_resolve_started",
                "identity_candidate_generated",
                "identity_review_required",
            ],
        )

    def test_resolver_keeps_draft_when_match_score_is_below_review_threshold(self) -> None:
        from wechat_ai.identity.identity_models import IdentityRawSignal, UserAlias, UserIdentity
        from wechat_ai.identity.identity_repository import IdentityRepository
        from wechat_ai.identity.identity_resolver import IdentityResolver

        repo = IdentityRepository(base_dir=self.make_temp_dir())
        repo.save_users(
            [
                UserIdentity(
                    user_id="user_alex",
                    canonical_name="Alex Chen",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_alex",
                    display_names=["Alex Chen"],
                    latest_seen_name="Alex Chen",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        resolver = IdentityResolver(repository=repo)

        result = resolver.resolve(
            IdentityRawSignal(
                conversation_id="friend:new-person",
                chat_type="friend",
                display_name="New Person",
                text="hello there",
                contexts=["first time reaching out"],
                captured_at="2026-04-23T12:01:00Z",
            )
        )

        self.assertEqual(result.identity_status, "draft")
        self.assertIsNone(result.resolved_user_id)
        self.assertEqual(len(repo.load_candidates()), 0)
        self.assertEqual(len(repo.load_draft_users()), 1)

    def test_repository_keeps_json_utf8_and_empty_defaults(self) -> None:
        from wechat_ai.identity.identity_repository import IdentityRepository

        base_dir = self.make_temp_dir()
        repo = IdentityRepository(base_dir=base_dir)

        self.assertEqual(repo.load_users(), [])
        repo.save_draft_users([])

        raw = (base_dir / "draft_users.json").read_text(encoding="utf-8")
        self.assertEqual(json.loads(raw), [])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIIdentityTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
