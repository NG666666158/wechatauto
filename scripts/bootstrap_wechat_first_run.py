from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _bootstrap import configure_comtypes_cache  # noqa: E402

configure_comtypes_cache(ROOT)

from pyweixin import Contacts, GlobalConfig, Messages, Tools  # noqa: E402
from wechat_ai.app.wechat_bootstrap import (  # noqa: E402
    BootstrapSettings,
    WeChatFirstRunBootstrapper,
    parse_guardian_command,
)


def _ui_ready_check():
    checks: dict[str, object] = {}
    try:
        profile = Contacts.check_my_info(close_weixin=False)
        if profile:
            checks["my_profile"] = profile
    except Exception:
        pass
    try:
        sessions = Messages.dump_recent_sessions(recent="Today", chat_only=False, close_weixin=False)
        if isinstance(sessions, list):
            checks["recent_sessions"] = sessions[:3]
    except Exception:
        pass
    try:
        new_messages = Messages.check_new_messages(close_weixin=False)
        if new_messages is not None:
            checks["new_messages"] = new_messages
    except Exception:
        pass
    return checks


def _locate_wechat_path() -> str:
    try:
        return str(Tools.where_weixin(copy_to_clipboard=False) or "").strip()
    except Exception:
        return ""


def _is_wechat_running() -> bool:
    try:
        return bool(Tools.is_weixin_running())
    except Exception:
        return False


def _configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    _configure_console_output()
    parser = argparse.ArgumentParser(description="首次引导启动微信、讲述人，并在扫码登录后自动启动守护脚本。")
    parser.add_argument("--ready-timeout", type=float, default=300.0, help="等待微信主界面可识别的最长秒数")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="检测微信主界面的轮询秒数")
    parser.add_argument("--narrator-settle-seconds", type=float, default=5.0, help="启动讲述人后等待其接管 UI 的秒数")
    parser.add_argument("--wechat-path", default="", help="显式指定微信路径，默认自动探测")
    parser.add_argument("--narrator-path", default="", help="显式指定讲述人路径，默认使用系统 Narrator.exe")
    parser.add_argument("--no-auto-stop-narrator", action="store_true", help="识别成功后不自动关闭讲述人")
    parser.add_argument("--no-start-guardian", action="store_true", help="识别成功后只校验环境，不自动启动守护")
    parser.add_argument("--wait-for-ui-ready", action="store_true", help="先做独立主界面预检，预检通过后再启动守护")
    parser.add_argument("--guardian-command", default="", help="自定义守护命令，留空则默认启动全局守护脚本")
    args = parser.parse_args()

    GlobalConfig.close_weixin = False
    GlobalConfig.is_maximize = False

    guardian_command = parse_guardian_command(args.guardian_command, ROOT)

    bootstrapper = WeChatFirstRunBootstrapper(
        ui_ready_check=_ui_ready_check,
        status_callback=lambda message: print(f"[bootstrap] {message}", flush=True),
        locate_wechat_path=lambda: args.wechat_path.strip() or _locate_wechat_path(),
        is_wechat_running=_is_wechat_running,
    )
    result = bootstrapper.run(
        BootstrapSettings(
            ready_timeout_seconds=args.ready_timeout,
            ready_poll_interval_seconds=args.poll_interval,
            narrator_settle_seconds=args.narrator_settle_seconds,
            auto_stop_narrator_on_success=not args.no_auto_stop_narrator,
            start_guardian=not args.no_start_guardian,
            wait_for_ui_ready_before_guardian=args.wait_for_ui_ready,
            guardian_command=guardian_command,
            wechat_path=args.wechat_path,
            narrator_path=args.narrator_path,
        )
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
