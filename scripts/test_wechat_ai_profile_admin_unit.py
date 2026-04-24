from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_profile_admin_tests"
TMP_ROOT.mkdir(exist_ok=True)


class WeChatAIProfileAdminTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_list_profile_documents_returns_existing_user_documents(self) -> None:
        from wechat_ai.profile.profile_admin import list_profile_documents
        from wechat_ai.profile.profile_store import ProfileStore

        tmpdir = self.make_temp_dir()
        store = ProfileStore(base_dir=tmpdir)
        first = store.load_user_profile("friend_a")
        first.display_name = "Friend A"
        store.save_user_profile(first)
        store.load_user_profile("friend_b")

        documents = list_profile_documents("user", base_dir=tmpdir)

        self.assertEqual([doc["user_id"] for doc in documents], ["friend_a", "friend_b"])
        self.assertEqual(documents[0]["display_name"], "Friend A")

    def test_load_profile_document_returns_missing_default(self) -> None:
        from wechat_ai.profile.profile_admin import load_profile_document

        tmpdir = self.make_temp_dir()

        document = load_profile_document("user", "missing_friend", base_dir=tmpdir)

        self.assertEqual(document["user_id"], "missing_friend")
        self.assertEqual(document["tags"], [])
        self.assertEqual(document["notes"], [])

    def test_update_profile_document_sets_user_tags_from_comma_string(self) -> None:
        from wechat_ai.profile.profile_admin import update_profile_document

        tmpdir = self.make_temp_dir()

        document = update_profile_document(
            "user",
            "friend_demo",
            {"tags": " vip, friend ,vip,, "},
            base_dir=tmpdir,
        )

        self.assertEqual(document["user_id"], "friend_demo")
        self.assertEqual(document["tags"], ["vip", "friend"])

    def test_update_profile_document_sets_agent_style_rules_from_comma_string(self) -> None:
        from wechat_ai.profile.profile_admin import update_profile_document

        tmpdir = self.make_temp_dir()

        document = update_profile_document(
            "agent",
            "assistant",
            {"style_rules": "简洁, 温和 ,避免术语"},
            base_dir=tmpdir,
        )

        self.assertEqual(document["agent_id"], "assistant")
        self.assertEqual(document["style_rules"], ["简洁", "温和", "避免术语"])

    def test_special_character_id_uses_safe_filename_and_preserves_original_id(self) -> None:
        from wechat_ai.profile.profile_admin import update_profile_document
        from wechat_ai.storage_names import safe_storage_name

        tmpdir = self.make_temp_dir()
        user_id = ' 张 三/\\:*?"<>| friend '

        document = update_profile_document("user", user_id, {"display_name": "张三"}, base_dir=tmpdir)
        profile_path = tmpdir / "users" / f"{safe_storage_name(user_id, fallback='unknown_user')}.json"

        self.assertTrue(profile_path.exists())
        self.assertFalse((tmpdir / "users" / f"{user_id}.json").exists())
        self.assertEqual(document["user_id"], user_id)
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["user_id"], user_id)

    def test_cli_outputs_json_with_chinese_unescaped(self) -> None:
        tmpdir = self.make_temp_dir()

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "profile_admin.py"),
                "--base-dir",
                str(tmpdir),
                "set",
                "--kind",
                "agent",
                "--id",
                "助手",
                "--field",
                "style_rules",
                "--value",
                "简洁,温和",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn('"agent_id": "助手"', result.stdout)
        self.assertIn('"style_rules": [', result.stdout)
        self.assertIn('"简洁"', result.stdout)
        self.assertNotIn("\\u52a9\\u624b", result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["style_rules"], ["简洁", "温和"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIProfileAdminTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
