from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


class ObservabilityScriptsTests(unittest.TestCase):
    def test_show_recent_logs_prints_latest_event(self) -> None:
        temp_root = TMP_ROOT / "observability_script_tests" / str(uuid4())
        temp_root.mkdir(parents=True, exist_ok=True)
        log_path = temp_root / "runtime_events.jsonl"
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": "2026-04-22T10:00:00Z", "event_type": "message_received", "chat_id": "older"}) + "\n")
            handle.write(json.dumps({"timestamp": "2026-04-22T10:01:00Z", "event_type": "message_sent", "chat_id": "newer"}) + "\n")

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "show_recent_logs.py"), "--limit", "1", "--log-file", str(log_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn('"event_type": "message_sent"', result.stdout)
        self.assertNotIn('"chat_id": "older"', result.stdout)

    def test_show_memory_summary_prints_stored_summary(self) -> None:
        temp_root = TMP_ROOT / "observability_script_tests" / str(uuid4())
        memory_dir = temp_root / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_path = memory_dir / "friend_demo.json"
        with memory_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "chat_id": "friend_demo",
                    "recent_conversation": [],
                    "summary_text": "Prefers bullet points.",
                    "last_updated": "2026-04-22T10:00:00Z",
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "show_memory_summary.py"), "--chat-id", "friend_demo", "--memory-dir", str(memory_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("chat_id: friend_demo", result.stdout)
        self.assertIn("Prefers bullet points.", result.stdout)

    def test_long_run_observer_summarizes_runtime_logs_and_anomalies(self) -> None:
        from scripts.long_run_observer import build_long_run_observation_report

        temp_root = TMP_ROOT / "observability_script_tests" / str(uuid4())
        temp_root.mkdir(parents=True, exist_ok=True)
        log_path = temp_root / "runtime_events.jsonl"
        events = [
            {"timestamp": "2026-04-24T00:00:00Z", "event_type": "heartbeat", "polls": 10},
            {"timestamp": "2026-04-24T00:01:00Z", "event_type": "message_received", "chat_id": "friend"},
            {"timestamp": "2026-04-24T00:01:05Z", "event_type": "message_sent", "chat_id": "friend"},
            {"timestamp": "2026-04-24T00:02:00Z", "event_type": "active_anchor_missed", "chat_id": "friend"},
            {"timestamp": "2026-04-24T00:03:00Z", "event_type": "message_send_unconfirmed", "chat_id": "friend"},
            {"timestamp": "2026-04-24T00:04:00Z", "event_type": "loop_error", "exception_type": "RuntimeError"},
        ]
        with log_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        report = build_long_run_observation_report(
            log_file=log_path,
            readiness_report={
                "checks": [
                    {"id": "wechat_process", "status": "ok"},
                    {"id": "ui_ready_probe", "status": "warn"},
                ]
            },
            window_probe_report={
                "probe": {
                    "ready": False,
                    "status": "warn",
                    "focus_recommendation": "focus_input",
                }
            },
            target_duration_minutes=30,
            recent_limit=10,
        )

        self.assertEqual(report["script"], "long_run_observer")
        self.assertTrue(report["safe_read_only"])
        self.assertEqual(report["target_duration_minutes"], 30)
        self.assertEqual(report["runtime_log"]["total_events"], 6)
        self.assertEqual(report["runtime_log"]["event_counts"]["message_sent"], 1)
        self.assertEqual(report["anomalies"]["loop_error_count"], 1)
        self.assertEqual(report["anomalies"]["send_unconfirmed_count"], 1)
        self.assertEqual(report["anomalies"]["active_anchor_missed_count"], 1)
        self.assertIn("ui_ready_probe", report["readiness"]["warn_check_ids"])
        self.assertEqual(report["window_probe"]["focus_recommendation"], "focus_input")
        self.assertIn("send_confirmation", report["diagnosis"])

    def test_long_run_observer_cli_writes_jsonl_report(self) -> None:
        temp_root = TMP_ROOT / "observability_script_tests" / str(uuid4())
        temp_root.mkdir(parents=True, exist_ok=True)
        log_path = temp_root / "runtime_events.jsonl"
        output_path = temp_root / "long_run_observer.jsonl"
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": "2026-04-24T00:00:00Z", "event_type": "heartbeat"}) + "\n")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "long_run_observer.py"),
                "--log-file",
                str(log_path),
                "--output",
                str(output_path),
                "--format",
                "json",
                "--skip-readiness",
                "--skip-window-probe",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        stdout_report = json.loads(result.stdout)
        self.assertEqual(stdout_report["runtime_log"]["total_events"], 1)
        self.assertTrue(output_path.exists())
        written_lines = output_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(written_lines), 1)
        self.assertEqual(json.loads(written_lines[0])["script"], "long_run_observer")


if __name__ == "__main__":
    unittest.main()
