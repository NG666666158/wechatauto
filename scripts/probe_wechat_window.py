from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from wechat_ai.app.wechat_window_probe import WeChatWindowProbe  # noqa: E402


def _wechat_is_running() -> bool:
    if platform.system().lower() != "windows":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    names = {row[0].strip().lower() for row in csv.reader(result.stdout.splitlines()) if row}
    return "wechat.exe" in names or "weixin.exe" in names


def build_probe_report(*, probe: object | None = None, recent_limit: int = 20) -> dict[str, object]:
    if probe is None and not _wechat_is_running():
        return {
            "script": "probe_wechat_window",
            "safe_read_only": True,
            "does_not_send_messages": True,
            "probe": {
                "ready": False,
                "status": "skipped",
                "reason": "未检测到微信进程，已跳过窗口控件探测。",
            },
        }
    active_probe = probe or WeChatWindowProbe.from_pyweixin()
    try:
        result = active_probe.probe_ui_ready(recent_limit=recent_limit)
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    except Exception as exc:
        payload = {
            "ready": False,
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "script": "probe_wechat_window",
        "safe_read_only": True,
        "does_not_send_messages": True,
        "probe": payload,
    }


def _format_text(report: dict[str, object]) -> str:
    probe = report.get("probe", {})
    if not isinstance(probe, dict):
        probe = {}
    lines = [
        "WeChat window probe",
        f"Safe read-only: {report['safe_read_only']}",
        f"Ready: {probe.get('ready')}",
        f"Status: {probe.get('status')}",
        f"Window ready: {probe.get('window_ready', '')}",
        f"Window minimized: {probe.get('window_minimized', '')}",
        f"Input ready: {probe.get('input_ready', '')}",
        f"Current chat: {probe.get('current_chat', '')}",
        f"Visible messages: {probe.get('visible_message_count', 0)}",
        f"Latest visible text: {probe.get('latest_visible_text', '')}",
    ]
    recommendation = str(probe.get("focus_recommendation", "")).strip()
    if recommendation:
        lines.append(f"Focus recommendation: {recommendation}")
    reason = str(probe.get("reason", "")).strip()
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only probe for the current WeChat desktop window.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--recent-limit", type=int, default=20)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_probe_report(recent_limit=args.recent_limit)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
