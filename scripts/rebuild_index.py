from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete the current local knowledge index and rebuild it from source files."
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="Optional index path to delete and rebuild.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum characters per chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Character overlap between adjacent chunks.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        from scripts.ingest_knowledge import build_index, default_index_path, print_summary, resolve_dependencies
    except ImportError as exc:
        print(
            "Knowledge index rebuild failed: missing ingestion script dependencies. "
            f"Import failed: {exc}",
            file=sys.stderr,
        )
        return 1

    args = parse_args()

    try:
        deps = resolve_dependencies()
        resolved_index_path = Path(args.index_path) if args.index_path is not None else default_index_path(
            deps["paths"]
        )

        replaced_existing = resolved_index_path.exists()

        summary = build_index(
            index_path=resolved_index_path,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except Exception as exc:
        print(f"Knowledge index rebuild failed: {exc}", file=sys.stderr)
        return 1

    prefix = (
        "Knowledge index rebuilt."
        if replaced_existing
        else "Knowledge index rebuilt (no previous index found)."
    )
    print_summary(summary, prefix=prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
