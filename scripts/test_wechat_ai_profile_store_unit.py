from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_profile_store_tests"
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


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIProfileStoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
