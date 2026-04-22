from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.memory.memory_store import MemoryStore  # type: ignore  # noqa: E402
from wechat_ai.paths import MEMORY_DIR  # type: ignore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Show stored memory summary for a chat.")
    parser.add_argument("--chat-id", required=True, help="Chat identifier used by the memory store")
    parser.add_argument("--memory-dir", type=Path, default=MEMORY_DIR, help="Memory directory path")
    args = parser.parse_args()

    store = MemoryStore(base_dir=args.memory_dir)
    record = store.load(args.chat_id)
    print(f"chat_id: {record.chat_id}")
    print(f"last_updated: {record.last_updated or '(never)'}")
    print("summary:")
    print(record.summary_text or "(empty)")
    print(f"recent_snapshots: {len(record.recent_conversation)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
