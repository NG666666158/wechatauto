from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class PowerShellLifecycleScriptsTests(unittest.TestCase):
    def test_dev_start_only_starts_frontend_and_backend(self) -> None:
        content = (SCRIPTS / "dev_start.ps1").read_text(encoding="utf-8")

        self.assertIn("uvicorn", content)
        self.assertIn("npm.cmd", content)
        self.assertIn("[int]$BackendPort = 8765", content)
        self.assertIn("backend_$BackendPort.log", content)
        self.assertNotIn("run_minimax_global_auto_reply.py", content)
        self.assertNotIn("bootstrap_wechat_first_run.py", content)

    def test_runtime_scripts_are_separate_from_dev_services(self) -> None:
        runtime_start = (SCRIPTS / "runtime_start.ps1").read_text(encoding="utf-8")
        runtime_stop = (SCRIPTS / "runtime_stop.ps1").read_text(encoding="utf-8")

        self.assertIn("run_minimax_global_auto_reply.py", runtime_start)
        self.assertIn("--force-stop-file", runtime_start)
        self.assertNotIn("next dev", runtime_start.lower())
        self.assertNotIn("uvicorn", runtime_start.lower())
        self.assertIn("force_stop.flag", runtime_stop)
        self.assertIn("runtime.pid", runtime_stop)
        self.assertNotIn(":3000", runtime_stop)
        self.assertNotIn(":8000", runtime_stop)

    def test_web_runtime_smoke_uses_bootstrap_flow(self) -> None:
        content = (SCRIPTS / "runtime_web_smoke_1min.ps1").read_text(encoding="utf-8")

        self.assertIn("/runtime/bootstrap-check", content)
        self.assertIn("/runtime/bootstrap-start", content)
        self.assertIn("/runtime/stop", content)
        self.assertIn("http://127.0.0.1:8765/api/v1", content)
        self.assertIn("[int]$ReadyTimeoutSeconds = 120", content)
        self.assertIn("ready_timeout_seconds = $ReadyTimeoutSeconds", content)
        self.assertIn("wait_for_ui_ready_before_guardian = $true", content)
        self.assertNotIn("http://127.0.0.1:8000/api/v1", content)
        self.assertNotIn("/runtime/start", content)

    def test_dev_stop_does_not_stop_runtime_worker(self) -> None:
        content = (SCRIPTS / "dev_stop.ps1").read_text(encoding="utf-8")

        self.assertIn("backend.pid", content)
        self.assertIn("frontend.pid", content)
        self.assertNotIn("runtime.pid", content)
        self.assertNotIn("force_stop.flag", content)


if __name__ == "__main__":
    unittest.main()
