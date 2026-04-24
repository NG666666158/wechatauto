from __future__ import annotations

import importlib
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ProfileConfigTests(unittest.TestCase):
    def load_config(self):
        sys.modules.pop("wechat_ai.config", None)
        return importlib.import_module("wechat_ai.config")

    def make_temp_dir(self) -> Path:
        path = ROOT / ".tmp_profile_config_tests" / uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_profile_settings_defaults_resolve_from_paths(self) -> None:
        config = self.load_config()

        settings = config.ProfileSettings.from_env()

        self.assertEqual(settings.default_active_agent_id, "default_assistant")
        self.assertEqual(settings.user_profile_dir, config.USERS_DIR)
        self.assertEqual(settings.agent_profile_dir, config.AGENTS_DIR)
        self.assertTrue(settings.profile_auto_create)

    def test_profile_settings_support_env_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "WECHAT_ACTIVE_AGENT_ID": "helper_bot",
                "WECHAT_USER_PROFILE_DIR": str(ROOT / "tmp-users"),
                "WECHAT_AGENT_PROFILE_DIR": str(ROOT / "tmp-agents"),
                "WECHAT_PROFILE_AUTO_CREATE": "0",
            },
            clear=False,
        ):
            config = self.load_config()
            settings = config.ProfileSettings.from_env()

        self.assertEqual(settings.default_active_agent_id, "helper_bot")
        self.assertEqual(settings.user_profile_dir, ROOT / "tmp-users")
        self.assertEqual(settings.agent_profile_dir, ROOT / "tmp-agents")
        self.assertFalse(settings.profile_auto_create)

    def test_profile_store_uses_profile_auto_create_env_by_default(self) -> None:
        tmpdir = self.make_temp_dir()
        with patch.dict(os.environ, {"WECHAT_PROFILE_AUTO_CREATE": "0"}, clear=False):
            sys.modules.pop("wechat_ai.config", None)
            from wechat_ai.profile.profile_store import ProfileStore
            from wechat_ai.storage_names import safe_storage_name

            store = ProfileStore(base_dir=tmpdir)

        profile = store.load_user_profile("friend/demo")

        self.assertEqual(profile.user_id, "friend/demo")
        self.assertFalse((tmpdir / "users" / f"{safe_storage_name('friend/demo', fallback='unknown_user')}.json").exists())

    def test_reply_settings_default_prompts_come_from_profile_defaults(self) -> None:
        config = self.load_config()

        settings = config.ReplySettings.from_env()

        self.assertEqual(
            settings.friend_system_prompt,
            config.DEFAULT_FRIEND_SYSTEM_PROMPT,
        )
        self.assertEqual(
            settings.group_system_prompt,
            config.DEFAULT_GROUP_SYSTEM_PROMPT,
        )
        self.assertEqual(settings.fallback_reply, config.DEFAULT_FALLBACK_REPLY)


if __name__ == "__main__":
    unittest.main()
