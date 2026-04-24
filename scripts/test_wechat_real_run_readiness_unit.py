from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WeChatRealRunReadinessScriptTests(unittest.TestCase):
    def test_script_outputs_key_readiness_checks_and_exits_zero(self) -> None:
        script = ROOT / "scripts" / "check_wechat_real_run_readiness.py"

        result = subprocess.run(
            [sys.executable, str(script), "--format", "json"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        check_ids = {item["id"] for item in payload["checks"]}
        manual_ids = {item["id"] for item in payload["manual_checklist"]}

        self.assertIn("wechat_process", check_ids)
        self.assertIn("wechat_path", check_ids)
        self.assertIn("narrator_state", check_ids)
        self.assertIn("ui_ready_probe", check_ids)
        self.assertIn("display_scaling", check_ids)
        self.assertIn("foreground_permissions", check_ids)
        self.assertIn("unread_order", manual_ids)
        self.assertIn("group_sender", manual_ids)
        self.assertIn("send_confirmation", manual_ids)
        self.assertTrue(payload["safe_to_run_without_wechat"])


if __name__ == "__main__":
    unittest.main()
