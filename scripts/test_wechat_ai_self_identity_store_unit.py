from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_self_identity_store_tests"
TMP_ROOT.mkdir(exist_ok=True)


class SelfIdentityStoreTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_load_defaults_when_files_are_missing(self) -> None:
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())

        global_profile = store.load_global_profile()
        relationship = store.load_relationship_profile("teacher")
        override = store.load_user_override("user_001")

        self.assertEqual(global_profile.profile_id, "global")
        self.assertEqual(global_profile.identity_facts, [])
        self.assertEqual(relationship.relationship, "teacher")
        self.assertEqual(relationship.identity_facts, [])
        self.assertEqual(override.user_id, "user_001")
        self.assertEqual(override.relationship_override, "")

    def test_round_trip_persists_profiles(self) -> None:
        from wechat_ai.self_identity.models import (
            GlobalSelfIdentityProfile,
            RelationshipSelfIdentityProfile,
            UserSelfIdentityOverride,
        )
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())
        store.save_global_profile(
            GlobalSelfIdentityProfile(display_name="碱水", identity_facts=["我是产品负责人"], constraints=["不要编造报价"])
        )
        store.save_relationship_profile(
            RelationshipSelfIdentityProfile(
                relationship="teacher",
                trigger_tags=["老师"],
                identity_facts=["我是 2023 级学生"],
            )
        )
        store.save_user_override(
            UserSelfIdentityOverride(
                user_id="user_001",
                relationship_override="teacher",
                identity_facts=["我是 3 班班长"],
            )
        )

        self.assertEqual(store.load_global_profile().display_name, "碱水")
        self.assertEqual(store.load_relationship_profile("teacher").trigger_tags, ["老师"])
        self.assertEqual(store.load_user_override("user_001").identity_facts, ["我是 3 班班长"])

    def test_list_relationships_and_overrides_reads_saved_files(self) -> None:
        from wechat_ai.self_identity.models import RelationshipSelfIdentityProfile, UserSelfIdentityOverride
        from wechat_ai.self_identity.store import SelfIdentityStore

        store = SelfIdentityStore(base_dir=self.make_temp_dir())
        store.save_relationship_profile(RelationshipSelfIdentityProfile(relationship="teacher"))
        store.save_relationship_profile(RelationshipSelfIdentityProfile(relationship="parent"))
        store.save_user_override(UserSelfIdentityOverride(user_id="user_001"))
        store.save_user_override(UserSelfIdentityOverride(user_id="user_002"))

        self.assertEqual(
            [item.relationship for item in store.list_relationship_profiles()],
            ["parent", "teacher"],
        )
        self.assertEqual(
            [item.user_id for item in store.list_user_overrides()],
            ["user_001", "user_002"],
        )

    def test_user_override_uses_safe_filename_and_preserves_original_id(self) -> None:
        from wechat_ai.self_identity.models import UserSelfIdentityOverride
        from wechat_ai.self_identity.store import SelfIdentityStore
        from wechat_ai.storage_names import safe_storage_name

        temp_dir = self.make_temp_dir()
        store = SelfIdentityStore(base_dir=temp_dir)
        user_id = ' 张/老师:?*"<>| '
        store.save_user_override(UserSelfIdentityOverride(user_id=user_id, relationship_override="teacher"))

        expected = temp_dir / "user_overrides" / f"{safe_storage_name(user_id, fallback='unknown_user')}.json"
        self.assertTrue(expected.exists())
        payload = json.loads(expected.read_text(encoding="utf-8"))
        self.assertEqual(payload["user_id"], user_id.strip())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfIdentityStoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
