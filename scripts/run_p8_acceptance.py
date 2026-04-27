from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.long_run_observer import build_long_run_observation_report  # noqa: E402


DURATION_PRESETS = {
    "smoke": 30,
    "stability": 120,
    "long": 480,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run P8 acceptance report entrypoint.")
    parser.add_argument(
        "--preset",
        choices=sorted(DURATION_PRESETS),
        default="smoke",
        help="Acceptance duration preset.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=None,
        help="Override preset duration in minutes.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "pretty"),
        default="json",
        help="Output format.",
    )
    return parser


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> int:
    _configure_utf8_stdio()
    args = build_parser().parse_args()
    duration = int(args.duration_minutes or DURATION_PRESETS[args.preset])
    report = build_long_run_observation_report(target_duration_minutes=duration)
    payload = json.dumps(report, ensure_ascii=False, indent=2 if args.format == "pretty" else None)
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
