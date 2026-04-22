import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

cache_dir = configure_comtypes_cache(ROOT)

from pyweixin import Tools  # noqa: E402


def main() -> int:
    print("pyweixin import: OK")
    print(f"comtypes cache: {cache_dir}")
    try:
        print(f"WeChat running: {Tools.is_weixin_running()}")
    except Exception as exc:
        print(f"WeChat running check failed: {type(exc).__name__}: {exc}")
    try:
        location = Tools.where_weixin(copy_to_clipboard=False)
        print(f"WeChat path: {location}")
    except Exception as exc:
        print(f"WeChat path lookup failed: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
