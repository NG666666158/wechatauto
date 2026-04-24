from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp" / "profile_store_tests"
TMP_ROOT.mkdir(exist_ok=True)


class WeChatAIProfileStoreTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_tag_manager_normalize_trims_deduplicates_and_preserves_order(self) -> None:
        from wechat_ai.profile.tag_manager import TagManager

        tags = ["  alpha  ", "beta", "alpha", "", " beta ", "gamma", "  "]

        self.assertEqual(TagManager.normalize(tags), ["alpha", "beta", "gamma"])

    def test_safe_storage_name_keeps_chinese_and_replaces_windows_unsafe_parts(self) -> None:
        from wechat_ai.storage_names import safe_storage_name

        original = ' 张 三 /\\:*?"<>| friend '
        safe_name = safe_storage_name(original, fallback="unknown")

        self.assertIn("张_三", safe_name)
        self.assertIn("friend", safe_name)
        for char in '/\\:*?"<>|':
            self.assertNotIn(char, safe_name)
        self.assertNotIn(" ", safe_name)
        self.assertEqual(safe_storage_name("   ", fallback="unknown"), "unknown")

    def test_safe_storage_name_caps_very_long_names_with_stable_hash(self) -> None:
        from wechat_ai.storage_names import safe_storage_name

        original = "联系人" * 100
        safe_name = safe_storage_name(original, fallback="unknown")

        self.assertLessEqual(len(safe_name), 120)
        self.assertEqual(safe_name, safe_storage_name(original, fallback="unknown"))
        self.assertRegex(safe_name, r"_[0-9a-f]{10}$")

    def test_load_user_profile_creates_default_file_when_missing(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)

        profile = store.load_user_profile("friend_demo")
        profile_path = tmpdir / "users" / "friend_demo.json"

        self.assertTrue(profile_path.exists())
        self.assertEqual(profile.user_id, "friend_demo")
        self.assertEqual(profile.tags, [])

        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["user_id"], "friend_demo")
        self.assertEqual(raw["tags"], [])

    def test_user_profile_uses_safe_filename_and_preserves_original_user_id(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)
        user_id = ' 张 三 /\\:*?"<>| friend '

        profile = store.load_user_profile(user_id)
        profile_path = tmpdir / "users" / f"{safe_storage_name(user_id, fallback='unknown_user')}.json"

        self.assertTrue(profile_path.exists())
        self.assertEqual(profile.user_id, user_id)
        self.assertFalse((tmpdir / "users" / f"{user_id}.json").exists())

        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["user_id"], user_id)

    def test_load_user_profile_does_not_create_missing_file_when_auto_create_disabled(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir, auto_create=False)
        user_id = ' 张 三 /\\:*?"<>| friend '

        profile = store.load_user_profile(user_id)
        profile_path = tmpdir / "users" / f"{safe_storage_name(user_id, fallback='unknown_user')}.json"

        self.assertEqual(profile.user_id, user_id)
        self.assertEqual(profile.tags, [])
        self.assertFalse(profile_path.exists())

    def test_load_user_profile_normalizes_existing_file_when_auto_create_disabled(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        user_id = ' 张 三 /\\:*?"<>| friend '
        profile_path = tmpdir / "users" / f"{safe_storage_name(user_id, fallback='unknown_user')}.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps({"user_id": user_id, "tags": [" vip ", "vip", ""]}, ensure_ascii=False),
            encoding="utf-8",
        )
        store = ProfileStore(base_dir=tmpdir, auto_create=False)

        profile = store.load_user_profile(user_id)

        self.assertEqual(profile.tags, ["vip"])
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["user_id"], user_id)
        self.assertEqual(raw["tags"], ["vip"])

    def test_save_user_profile_normalizes_tags_and_round_trips(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)
        profile = store.load_user_profile("friend_demo")
        profile.tags = [" vip ", "vip", "friend", "friend ", ""]

        store.save_user_profile(profile)
        reloaded = store.load_user_profile("friend_demo")

        self.assertEqual(reloaded.user_id, "friend_demo")
        self.assertEqual(reloaded.tags, ["vip", "friend"])

    def test_load_agent_profile_creates_default_file_when_missing(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)

        profile = store.load_agent_profile("default_assistant")
        profile_path = tmpdir / "agents" / "default_assistant.json"

        self.assertTrue(profile_path.exists())
        self.assertEqual(profile.agent_id, "default_assistant")
        self.assertEqual(profile.style_rules, [])
        self.assertEqual(profile.goals, [])
        self.assertEqual(profile.forbidden_rules, [])

        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["agent_id"], "default_assistant")

    def test_agent_profile_uses_safe_filename_and_preserves_original_agent_id(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)
        agent_id = ' 机器人 /\\:*?"<>| helper '

        profile = store.load_agent_profile(agent_id)
        profile_path = tmpdir / "agents" / f"{safe_storage_name(agent_id, fallback='unknown_agent')}.json"

        self.assertTrue(profile_path.exists())
        self.assertEqual(profile.agent_id, agent_id)
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["agent_id"], agent_id)

    def test_load_agent_profile_does_not_create_missing_file_when_auto_create_disabled(self) -> None:
        from wechat_ai.profile.profile_store import ProfileStore
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir, auto_create=False)
        agent_id = ' 机器人 /\\:*?"<>| helper '

        profile = store.load_agent_profile(agent_id)
        profile_path = tmpdir / "agents" / f"{safe_storage_name(agent_id, fallback='unknown_agent')}.json"

        self.assertEqual(profile.agent_id, agent_id)
        self.assertEqual(profile.style_rules, [])
        self.assertEqual(profile.goals, [])
        self.assertEqual(profile.forbidden_rules, [])
        self.assertFalse(profile_path.exists())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIProfileStoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
