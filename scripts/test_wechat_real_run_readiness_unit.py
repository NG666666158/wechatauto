from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def _load_readiness_module():
    script = ROOT / "scripts" / "check_wechat_real_run_readiness.py"
    spec = importlib.util.spec_from_file_location("check_wechat_real_run_readiness_under_test", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
        self.assertIn("desktop_window_enumeration", check_ids)
        self.assertIn("ui_ready_probe", check_ids)
        self.assertIn("display_scaling", check_ids)
        self.assertIn("foreground_permissions", check_ids)
        self.assertIn("unread_order", manual_ids)
        self.assertIn("group_sender", manual_ids)
        self.assertIn("send_confirmation", manual_ids)
        self.assertTrue(payload["safe_to_run_without_wechat"])

    def test_process_check_falls_back_when_tasklist_is_denied(self) -> None:
        module = _load_readiness_module()

        denied = subprocess.CompletedProcess(
            args=["tasklist"],
            returncode=1,
            stdout="",
            stderr="ERROR: Access denied",
        )

        def fake_is_running(name: str) -> bool:
            return name == "Weixin.exe"

        with patch.object(module.subprocess, "run", return_value=denied), patch.object(
            module,
            "is_process_running",
            side_effect=fake_is_running,
        ):
            names = module._windows_process_names()

        self.assertIn("weixin.exe", names)
        self.assertNotIn("wechat.exe", names)


if __name__ == "__main__":
    unittest.main()
