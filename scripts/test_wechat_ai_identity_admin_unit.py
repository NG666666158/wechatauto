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
TMP_ROOT = ROOT / ".tmp" / "identity_admin_tests"
TMP_ROOT.mkdir(exist_ok=True)


class WeChatAIIdentityAdminTests(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        path = TMP_ROOT / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def seed_identity_data(self, base_dir: Path) -> None:
        from wechat_ai.identity.identity_models import DraftUser, IdentityCandidate, UserAlias, UserIdentity
        from wechat_ai.identity.identity_repository import IdentityRepository

        repo = IdentityRepository(base_dir=base_dir)
        repo.save_users(
            [
                UserIdentity(
                    user_id="user_000001",
                    canonical_name="张三",
                    user_type="客户",
                    relationship_to_me="供应商客户",
                    status="confirmed",
                    created_at="2026-04-23T12:00:00Z",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        repo.save_aliases(
            [
                UserAlias(
                    user_id="user_000001",
                    display_names=["张总"],
                    latest_seen_name="张总",
                    updated_at="2026-04-23T12:00:00Z",
                )
            ]
        )
        repo.save_draft_users(
            [
                DraftUser(
                    draft_user_id="draft_000001",
                    proposed_name="李四",
                    proposed_user_type="客户",
                    relationship_to_me="潜在客户",
                    source_signals=["message_contains_order_keywords"],
                    conversation_id="friend:李四",
                    created_at="2026-04-23T12:01:00Z",
                    updated_at="2026-04-23T12:01:00Z",
                )
            ]
        )
        repo.save_candidates(
            [
                IdentityCandidate(
                    candidate_id="candidate_000001",
                    incoming_name="老张",
                    matched_user_id="user_000001",
                    confidence=0.92,
                    evidence=["alias_fuzzy_match"],
                )
            ]
        )

    def test_list_functions_return_serializable_documents(self) -> None:
        from wechat_ai.identity.identity_admin import list_candidates, list_drafts, list_users

        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        users = list_users(base_dir=tmpdir)
        drafts = list_drafts(base_dir=tmpdir)
        candidates = list_candidates(base_dir=tmpdir)

        self.assertEqual(users[0]["user_id"], "user_000001")
        self.assertEqual(users[0]["canonical_name"], "张三")
        self.assertEqual(drafts[0]["draft_user_id"], "draft_000001")
        self.assertEqual(candidates[0]["candidate_id"], "candidate_000001")
        self.assertEqual(candidates[0]["status"], "pending_review")

    def test_confirm_draft_creates_user_and_alias_when_user_missing(self) -> None:
        from wechat_ai.identity.identity_admin import confirm_draft
        from wechat_ai.identity.identity_repository import IdentityRepository

        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        payload = confirm_draft("draft_000001", user_id=None, base_dir=tmpdir)

        repo = IdentityRepository(base_dir=tmpdir)
        users = repo.load_users()
        aliases = repo.load_aliases()
        drafts = repo.load_draft_users()

        self.assertTrue(payload["user"]["user_id"].startswith("user_"))
        self.assertEqual(payload["user"]["canonical_name"], "李四")
        self.assertEqual(payload["draft"]["status"], "confirmed")
        self.assertEqual(len(users), 2)
        self.assertIn("李四", [alias.latest_seen_name for alias in aliases])
        self.assertEqual(drafts[0].status, "confirmed")

    def test_confirm_draft_can_attach_to_existing_user(self) -> None:
        from wechat_ai.identity.identity_admin import confirm_draft
        from wechat_ai.identity.identity_repository import IdentityRepository

        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        payload = confirm_draft("draft_000001", user_id="user_000001", base_dir=tmpdir)

        repo = IdentityRepository(base_dir=tmpdir)
        users = repo.load_users()
        aliases = repo.load_aliases()

        self.assertEqual(payload["user"]["user_id"], "user_000001")
        self.assertEqual(len(users), 1)
        self.assertIn("李四", aliases[0].display_names)

    def test_merge_candidate_adds_alias_and_marks_candidate_merged(self) -> None:
        from wechat_ai.identity.identity_admin import merge_candidate
        from wechat_ai.identity.identity_repository import IdentityRepository

        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        payload = merge_candidate("candidate_000001", base_dir=tmpdir)

        repo = IdentityRepository(base_dir=tmpdir)
        aliases = repo.load_aliases()
        candidates = repo.load_candidates()

        self.assertEqual(payload["candidate"]["status"], "merged")
        self.assertIn("老张", aliases[0].display_names)
        self.assertEqual(candidates[0].status, "merged")

    def test_add_alias_supports_group_name(self) -> None:
        from wechat_ai.identity.identity_admin import add_alias
        from wechat_ai.identity.identity_repository import IdentityRepository

        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        payload = add_alias("user_000001", "小张", group_name="供货群", base_dir=tmpdir)

        repo = IdentityRepository(base_dir=tmpdir)
        aliases = repo.load_aliases()

        self.assertEqual(payload["user_id"], "user_000001")
        self.assertIn({"group_name": "供货群", "name": "小张"}, aliases[0].group_nicknames)

    def test_cli_confirm_draft_outputs_json_without_ascii_escaping(self) -> None:
        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "identity_admin.py"),
                "--base-dir",
                str(tmpdir),
                "confirm-draft",
                "--draft-id",
                "draft_000001",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn('"canonical_name": "李四"', result.stdout)
        self.assertNotIn("\\u674e\\u56db", result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["draft"]["draft_user_id"], "draft_000001")

    def test_cli_merge_candidate_outputs_json(self) -> None:
        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "identity_admin.py"),
                "--base-dir",
                str(tmpdir),
                "merge-candidate",
                "--candidate-id",
                "candidate_000001",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["candidate"]["status"], "merged")
        self.assertEqual(payload["alias"]["latest_seen_name"], "老张")

    def test_cli_add_alias_outputs_group_alias_json(self) -> None:
        tmpdir = self.make_temp_dir()
        self.seed_identity_data(tmpdir)

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "identity_admin.py"),
                "--base-dir",
                str(tmpdir),
                "add-alias",
                "--user-id",
                "user_000001",
                "--name",
                "阿张",
                "--group-name",
                "项目群",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["group_nicknames"], [{"group_name": "项目群", "name": "阿张"}])
        self.assertNotIn("\\u9879\\u76ee\\u7fa4", result.stdout)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatAIIdentityAdminTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
