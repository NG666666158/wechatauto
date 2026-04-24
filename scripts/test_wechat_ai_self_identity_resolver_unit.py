from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_self_identity_resolver_tests"
TMP_ROOT.mkdir(exist_ok=True)


class SelfIdentityResolverTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_resolver_merges_global_relationship_and_override_by_priority(self) -> None:
        from wechat_ai.profile.user_profile import UserProfile
        from wechat_ai.self_identity.models import (
            GlobalSelfIdentityProfile,
            RelationshipSelfIdentityProfile,
            UserSelfIdentityOverride,
        )
        from wechat_ai.self_identity.resolver import SelfIdentityResolver
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())
        store.save_global_profile(GlobalSelfIdentityProfile(identity_facts=["我是产品负责人"], constraints=["不要编造身份"]))
        store.save_relationship_profile(
            RelationshipSelfIdentityProfile(relationship="teacher", identity_facts=["我是 2023 级学生"])
        )
        store.save_user_override(
            UserSelfIdentityOverride(
                user_id="user_001",
                relationship_override="teacher",
                identity_facts=["我是 3 班班长"],
            )
        )

        resolver = SelfIdentityResolver(store)
        resolved = resolver.resolve(
            user_id="user_001",
            user_profile=UserProfile(user_id="user_001", tags=["朋友"]),
            relationship_to_me="parent",
        )

        self.assertEqual(resolved.relationship, "teacher")
        self.assertEqual(resolved.identity_facts, ["我是产品负责人", "我是 2023 级学生", "我是 3 班班长"])
        self.assertIn("事实: 我是 3 班班长", resolved.summary)

    def test_resolver_uses_user_tags_when_no_override_exists(self) -> None:
        from wechat_ai.profile.user_profile import UserProfile
        from wechat_ai.self_identity.models import RelationshipSelfIdentityProfile
        from wechat_ai.self_identity.resolver import SelfIdentityResolver
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())
        store.save_relationship_profile(RelationshipSelfIdentityProfile(relationship="customer", identity_facts=["我是售前答疑人"]))
        resolver = SelfIdentityResolver(store)

        resolved = resolver.resolve(
            user_id="user_002",
            user_profile=UserProfile(user_id="user_002", tags=["客户"]),
        )

        self.assertEqual(resolved.relationship, "customer")
        self.assertEqual(resolved.identity_facts, ["我是售前答疑人"])

    def test_resolver_returns_global_only_when_no_relationship_source(self) -> None:
        from wechat_ai.self_identity.models import GlobalSelfIdentityProfile
        from wechat_ai.self_identity.resolver import SelfIdentityResolver
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())
        store.save_global_profile(GlobalSelfIdentityProfile(identity_facts=["我是碱水"], constraints=["别乱承诺"]))
        resolver = SelfIdentityResolver(store)

        resolved = resolver.resolve(user_id="user_003")

        self.assertEqual(resolved.relationship, "")
        self.assertEqual(resolved.identity_facts, ["我是碱水"])
        self.assertEqual(resolved.constraints, ["别乱承诺"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfIdentityResolverTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
