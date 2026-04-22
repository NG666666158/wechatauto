from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from wechat_ai.wechat_runtime import WeChatAIApp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run global MiniMax-powered auto reply for unread WeChat sessions.")
    parser.add_argument("--duration", default="5min", help="Total running duration, e.g. 30s / 5min / 1h")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--debug", action="store_true", help="Print runtime debug logs")
    parser.add_argument("--active-merge-window", type=float, default=3.0, help="Merge window for the currently open chat in seconds")
    args = parser.parse_args()

    app = WeChatAIApp.from_env()
    app.debug = args.debug
    app.active_merge_window = args.active_merge_window
    result = app.run_global_auto_reply(
        duration=args.duration,
        poll_interval=args.poll_interval,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
