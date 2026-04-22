from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ProfileConfigTests(unittest.TestCase):
    def load_config(self):
        sys.modules.pop("wechat_ai.config", None)
        return importlib.import_module("wechat_ai.config")

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
