from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class P8ShellAcceptanceTests(unittest.TestCase):
    def test_shell_acceptance_source_checks_are_present(self) -> None:
        from scripts.run_p8_shell_acceptance import build_shell_acceptance_report

        report = build_shell_acceptance_report(skip_http=True)

        self.assertEqual(report["script"], "p8_shell_acceptance")
        self.assertTrue(report["checks"]["settings_source"]["labels_present"])
        self.assertTrue(report["checks"]["settings_source"]["settings_tokens_present"])
        self.assertTrue(report["checks"]["settings_source"]["bridge_tokens_present"])
        self.assertTrue(report["checks"]["window_diagnostics"]["events_present"])
        self.assertEqual(report["checks"]["frontend_probe"]["error"], "skipped")

    def test_shell_acceptance_http_probe_checks_settings_labels(self) -> None:
        from scripts.run_p8_shell_acceptance import build_shell_acceptance_report

        server = ThreadingHTTPServer(("127.0.0.1", 0), _SettingsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            report = build_shell_acceptance_report(
                frontend_url=f"http://127.0.0.1:{server.server_port}/settings",
                skip_http=False,
                timeout_seconds=2.0,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertTrue(report["accepted"])
        self.assertTrue(report["checks"]["frontend_probe"]["reachable"])
        self.assertTrue(report["checks"]["frontend_probe"]["labels_present"])
        self.assertEqual(report["checks"]["frontend_probe"]["status_code"], 200)

    def test_shell_acceptance_cli_outputs_json(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_p8_shell_acceptance.py"),
                "--skip-http",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["script"], "p8_shell_acceptance")
        self.assertTrue(payload["accepted"])


class _SettingsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = """
        <html>
          <body>
            <div>开机自启</div>
            <div>定时巡检间隔</div>
          </body>
        </html>
        """.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    unittest.main()
