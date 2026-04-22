from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ObservabilityScriptsTests(unittest.TestCase):
    def test_show_recent_logs_prints_latest_event(self) -> None:
        temp_root = ROOT / ".tmp_observability_script_tests" / str(uuid4())
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
        temp_root = ROOT / ".tmp_observability_script_tests" / str(uuid4())
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


if __name__ == "__main__":
    unittest.main()
