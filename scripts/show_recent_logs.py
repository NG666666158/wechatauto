from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.logging_utils import RUNTIME_LOG_FILE, tail_jsonl_events  # type: ignore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Show recent structured WeChat AI runtime events.")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent events to print")
    parser.add_argument("--log-file", type=Path, default=RUNTIME_LOG_FILE, help="JSONL log file path")
    args = parser.parse_args()

    events = tail_jsonl_events(limit=args.limit, path=args.log_file)
    if not events:
        print(f"No events found in {args.log_file}")
        return 0

    for event in events:
        print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
