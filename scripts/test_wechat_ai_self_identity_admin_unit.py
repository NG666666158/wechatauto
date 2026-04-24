from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_self_identity_admin_tests"
TMP_ROOT.mkdir(exist_ok=True)


class SelfIdentityAdminTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_admin_crud_and_preview(self) -> None:
        from wechat_ai.self_identity import admin

        temp_dir = self.make_temp_dir()
        global_profile = admin.update_global_profile({"display_name": "碱水", "identity_facts": ["我是产品负责人"]}, base_dir=temp_dir)
        relationship = admin.update_relationship_profile(
            "teacher",
            {"identity_facts": ["我是 2023 级学生"], "trigger_tags": ["老师"]},
            base_dir=temp_dir,
        )
        override = admin.update_user_override(
            "user_001",
            {"relationship_override": "teacher", "identity_facts": ["我是 3 班班长"]},
            base_dir=temp_dir,
        )
        preview = admin.preview_resolved_profile("user_001", tags=["朋友"], base_dir=temp_dir)

        self.assertEqual(global_profile["display_name"], "碱水")
        self.assertEqual(relationship["relationship"], "teacher")
        self.assertEqual(override["user_id"], "user_001")
        self.assertEqual(preview["relationship"], "teacher")
        self.assertIn("我是 3 班班长", preview["identity_facts"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfIdentityAdminTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
