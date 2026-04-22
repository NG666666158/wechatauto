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
    parser = argparse.ArgumentParser(description="Run MiniMax-powered group @ auto reply.")
    parser.add_argument("--group", required=True, help="Group remark/name in WeChat")
    parser.add_argument("--duration", default="5min", help="Listen duration, e.g. 30s / 5min / 1h")
    parser.add_argument("--debug", action="store_true", help="Print runtime debug logs")
    args = parser.parse_args()

    app = WeChatAIApp.from_env()
    app.debug = args.debug
    result = app.run_group_at_auto_reply(
        group_name=args.group,
        duration=args.duration,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
