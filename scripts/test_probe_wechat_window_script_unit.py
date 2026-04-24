from __future__ import annotations

import sys
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeProbeResult:
    def to_dict(self) -> dict[str, object]:
        return {
            "ready": True,
            "status": "ok",
            "current_chat": "张先生",
            "visible_message_count": 2,
            "latest_visible_text": "你好",
            "window_ready": True,
            "window_minimized": False,
            "input_ready": True,
            "focus_recommendation": "",
        }


class FakeProbe:
    def probe_ui_ready(self, *, recent_limit: int = 20):
        return FakeProbeResult()


class ProbeWechatWindowScriptTests(TestCase):
    def test_build_probe_report_wraps_probe_result(self) -> None:
        from scripts.probe_wechat_window import build_probe_report

        report = build_probe_report(probe=FakeProbe(), recent_limit=5)

        self.assertTrue(report["safe_read_only"])
        self.assertEqual(report["probe"]["ready"], True)
        self.assertEqual(report["probe"]["current_chat"], "张先生")

    def test_text_report_includes_focus_readiness_fields(self) -> None:
        from scripts.probe_wechat_window import _format_text, build_probe_report

        report = build_probe_report(probe=FakeProbe(), recent_limit=5)
        text = _format_text(report)

        self.assertIn("Window ready: True", text)
        self.assertIn("Window minimized: False", text)
        self.assertIn("Input ready: True", text)


if __name__ == "__main__":
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProbeWechatWindowScriptTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
