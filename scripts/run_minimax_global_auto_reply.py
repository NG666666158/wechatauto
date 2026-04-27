from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from wechat_ai import paths  # noqa: E402
from wechat_ai.wechat_runtime import EmergencyStopWatcher, WeChatAIApp, _build_force_stop_hotkey_monitor  # noqa: E402


def _configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    _configure_console_output()
    parser = argparse.ArgumentParser(description="Run global MiniMax-powered auto reply for unread WeChat sessions.")
    parser.add_argument("--duration", default="5min", help="Total running duration, e.g. 30s / 5min / 1h")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--debug", action="store_true", help="Print runtime debug logs")
    parser.add_argument("--active-merge-window", type=float, default=3.0, help="Merge window for the currently open chat in seconds")
    parser.add_argument("--forever", action="store_true", help="Run continuously until interrupted")
    parser.add_argument("--heartbeat-interval", type=float, default=60.0, help="Heartbeat event interval in seconds; set <= 0 to disable")
    parser.add_argument("--error-backoff-seconds", type=float, default=5.0, help="Base retry backoff in seconds after loop errors")
    parser.add_argument("--force-stop-hotkey", default="ctrl+shift+f12", help="Global force-stop hotkey, e.g. ctrl+shift+f12; use 'off' to disable")
    parser.add_argument(
        "--force-stop-file",
        default=str(paths.DATA_DIR / "app" / "force_stop.flag"),
        help="Emergency stop flag file watched by a background thread.",
    )
    args = parser.parse_args()

    stop_file = Path(args.force_stop_file)
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        stop_file.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        stop_file.write_text("", encoding="utf-8")

    def emergency_exit(reason: str) -> None:
        print(f"[wechat_ai] emergency stop triggered reason={reason}", flush=True)
        os._exit(130)

    watcher = EmergencyStopWatcher(
        hotkey_monitor=_build_force_stop_hotkey_monitor(args.force_stop_hotkey),
        stop_file=stop_file,
        on_trigger=emergency_exit,
    ).start()

    app = WeChatAIApp.from_env()
    app.debug = args.debug
    app.active_merge_window = args.active_merge_window
    try:
        result = app.run_global_auto_reply(
            duration=args.duration,
            poll_interval=args.poll_interval,
            forever=args.forever,
            heartbeat_interval=args.heartbeat_interval,
            error_backoff_seconds=args.error_backoff_seconds,
            stop_hotkey=args.force_stop_hotkey,
        )
    finally:
        watcher.stop()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
