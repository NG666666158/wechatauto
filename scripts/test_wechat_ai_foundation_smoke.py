from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    modules = [
        "wechat_ai.models",
        "wechat_ai.paths",
        "wechat_ai.reply_engine",
        "wechat_ai.wechat_runtime",
    ]
    loaded: list[str] = []
    try:
        for module_name in modules:
            importlib.import_module(module_name)
            loaded.append(module_name)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "loaded": loaded,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps({"ok": True, "loaded": loaded}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
