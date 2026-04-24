from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from pyweixin import Contacts, GlobalConfig, Messages, Tools  # noqa: E402


def _configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def run_step(name, func):
    try:
        value = func()
        return {"ok": True, "value": value}
    except Exception as exc:  # pragma: no cover - smoke script
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    _configure_console_output()
    GlobalConfig.close_weixin = False
    GlobalConfig.is_maximize = False

    results = {
        "wechat_running": run_step("wechat_running", Tools.is_weixin_running),
        "wechat_path": run_step("wechat_path", lambda: Tools.where_weixin(copy_to_clipboard=False)),
        "my_profile": run_step("my_profile", lambda: Contacts.check_my_info(close_weixin=False)),
        "recent_sessions": run_step(
            "recent_sessions",
            lambda: Messages.dump_recent_sessions(recent="Today", chat_only=False, close_weixin=False)[:5],
        ),
        "new_messages": run_step("new_messages", lambda: Messages.check_new_messages(close_weixin=False)),
    }

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["ok"] for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
