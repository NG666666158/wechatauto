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

from pyweixin import GlobalConfig, Tools  # noqa: E402
from pyweixin.Errors import NetWorkError, NotFoundError, NotLoginError, NotStartError  # noqa: E402
from pyweixin.WeChatTools import Navigator, desktop, wx  # noqa: E402
from wechat_ai.app.wechat_bootstrap import (  # noqa: E402
    BootstrapSettings,
    WeChatFirstRunBootstrapper,
    parse_guardian_command,
)

_ENTER_WECHAT_CLICKED = False


def _ui_ready_check():
    checks: dict[str, object] = {}
    errors: dict[str, str] = {}
    _reset_wechat_window_cache()
    if _click_enter_wechat_if_present():
        checks["enter_wechat_clicked"] = True
        return {"ready": False, "checks": checks, "errors": errors}
    try:
        main_window = Navigator.open_weixin(is_maximize=False)
        checks["main_window"] = {
            "handle": int(getattr(main_window, "handle", 0) or 0),
            "class_name": main_window.class_name(),
        }
        return {"ready": True, "checks": checks, "errors": errors}
    except (NotStartError, NotFoundError, NotLoginError, NetWorkError) as exc:
        errors["main_window"] = f"{type(exc).__name__}: {exc}"
        checks["state"] = type(exc).__name__
    except Exception as exc:
        errors["main_window"] = f"{type(exc).__name__}: {exc}"
        checks["state"] = "unknown_error"
    return {"ready": False, "checks": checks, "errors": errors}


def _reset_wechat_window_cache() -> None:
    try:
        wx.hwnd = 0
        wx.possible_windows = []
        wx.window_type = 1
    except Exception:
        pass


def _click_enter_wechat_if_present() -> bool:
    global _ENTER_WECHAT_CLICKED
    if _ENTER_WECHAT_CLICKED:
        return False
    try:
        _reset_wechat_window_cache()
        handle = wx.find_wx_window()
        if not handle:
            return False
        window = desktop.window(handle=handle)
        enter_button = window.child_window(title="进入微信", control_type="Button")
        if not enter_button.exists(timeout=0.1):
            return False
        print("[bootstrap] 检测到进入微信按钮，点击后继续等待主界面。", flush=True)
        enter_button.click_input()
        _ENTER_WECHAT_CLICKED = True
        return True
    except Exception:
        return False


def _locate_wechat_path() -> str:
    try:
        detected = str(Tools.where_weixin(copy_to_clipboard=False) or "").strip()
        if detected:
            return detected
    except Exception:
        pass
    for candidate in (
        Path(r"C:\Weixin\Weixin.exe"),
        Path.home() / r"AppData\Local\Tencent\Weixin\Weixin.exe",
        Path.home() / r"AppData\Roaming\Tencent\Weixin\Weixin.exe",
    ):
        if candidate.exists():
            return str(candidate)
    return r"C:\Weixin\Weixin.exe"


def _is_wechat_running() -> bool:
    try:
        return bool(Tools.is_weixin_running())
    except Exception:
        return False


def _is_wechat_window_available() -> bool:
    try:
        return bool(Tools.is_weixin_running() and wx.find_wx_window())
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
        is_wechat_window_available=_is_wechat_window_available,
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
