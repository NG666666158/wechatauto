from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from pyweixin import GlobalConfig, Messages  # noqa: E402


def main() -> int:
    GlobalConfig.close_weixin = False
    GlobalConfig.is_maximize = False

    result = {}
    try:
        result["messages"] = Messages.pull_messages(friend="文件传输助手", number=3, close_weixin=False)
        result["ok"] = True
    except Exception as exc:  # pragma: no cover - live regression script
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
