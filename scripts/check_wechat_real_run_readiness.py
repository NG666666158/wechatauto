from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wechat_ai.app.wechat_bootstrap import is_process_running  # noqa: E402


WECHAT_PROCESS_NAMES = ("WeChat.exe", "Weixin.exe")
NARRATOR_PROCESS_NAME = "Narrator.exe"


@dataclass(frozen=True)
class CheckItem:
    id: str
    title: str
    status: str
    detail: str
    recommendation: str


@dataclass(frozen=True)
class ManualChecklistItem:
    id: str
    title: str
    detail: str
    expected_result: str


def _windows_process_names() -> set[str]:
    if platform.system().lower() != "windows":
        return set()
    expected_processes = (*WECHAT_PROCESS_NAMES, NARRATOR_PROCESS_NAME)
    names: set[str] = set()
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0:
        for row in csv.reader(result.stdout.splitlines()):
            if row:
                names.add(row[0].strip().lower())

    # Some locked-down Windows sessions deny tasklist/WMI even though pywinauto
    # can still see WeChat. Reuse the bootstrapper's Get-Process fallback so
    # readiness agrees with the real launcher path.
    for process_name in expected_processes:
        if process_name.lower() in names:
            continue
        try:
            if is_process_running(process_name):
                names.add(process_name.lower())
        except Exception:
            continue
    return names


def _candidate_wechat_paths() -> list[Path]:
    candidates: list[Path] = []
    env_names = ("WECHAT_PATH", "WEIXIN_PATH")
    for env_name in env_names:
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))

    candidates.extend(
        [
            Path(r"C:\Weixin\Weixin.exe"),
            Path(r"C:\Program Files\Tencent\WeChat\WeChat.exe"),
            Path(r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"),
        ]
    )

    for base_env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(base_env)
        if not base:
            continue
        base_path = Path(base)
        candidates.extend(
            [
                base_path / "Tencent" / "WeChat" / "WeChat.exe",
                base_path / "Tencent" / "Weixin" / "Weixin.exe",
                base_path / "WeChat" / "WeChat.exe",
                base_path / "Weixin" / "Weixin.exe",
            ]
        )

    return list(dict.fromkeys(candidates))


def _existing_wechat_paths() -> list[str]:
    return [str(path) for path in _candidate_wechat_paths() if path.exists()]


def _display_scaling_detail() -> tuple[str, str]:
    if platform.system().lower() != "windows":
        return ("info", "非 Windows 环境，跳过自动 DPI 探测。")
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        return ("manual", "无法读取系统 DPI，请在 Windows 显示设置中人工确认缩放比例。")
    scale = round(dpi / 96 * 100)
    if scale == 100:
        return ("ok", "当前系统缩放约为 100%，最利于 UI 自动化坐标稳定。")
    return (
        "warn",
        f"当前系统缩放约为 {scale}%，真实联调前建议记录该值；若控件定位不稳，优先尝试 100%。",
    )


def _desktop_window_enumeration_detail() -> tuple[str, str, str]:
    if platform.system().lower() != "windows":
        return ("info", "非 Windows 环境，跳过桌面窗口枚举。", "仅 Windows 真实联调需要校验这一项。")
    try:
        import win32gui  # type: ignore
    except Exception as exc:
        return (
            "manual",
            f"无法导入 win32gui：{type(exc).__name__}: {exc}",
            "请确认 pywin32 可用；否则 UI 自动化无法稳定探测微信窗口。",
        )

    total = 0
    visible = 0

    def _callback(hwnd: int, _param: object) -> bool:
        nonlocal total, visible
        total += 1
        try:
            if win32gui.IsWindowVisible(hwnd):
                visible += 1
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_callback, None)
    except Exception as exc:
        return (
            "warn",
            f"当前执行上下文无法枚举桌面窗口：{type(exc).__name__}: {exc}",
            "请从与微信相同的交互式桌面/权限级别启动后端或真实监听脚本。",
        )
    if total <= 0:
        return (
            "warn",
            "当前执行上下文枚举到 0 个桌面窗口；UIA/Win32 看不到真实桌面。",
            "请不要在该上下文启动真实监听。改用你手动打开的 PowerShell/客户端进程启动，确保它和微信在同一交互式桌面。",
        )
    return (
        "ok",
        f"当前执行上下文可枚举桌面窗口：total={total}, visible={visible}。",
        "可以继续执行只读微信窗口探测；真实监听前仍需确认微信主窗口未最小化。",
    )


def _ui_probe_check(wechat_running: bool) -> CheckItem:
    if not wechat_running:
        return CheckItem(
            id="ui_ready_probe",
            title="UI ready 只读探测",
            status="manual",
            detail="未检测到微信进程，已跳过窗口控件探测。",
            recommendation="登录微信并保持主窗口可见后，可运行 py -3 scripts\\probe_wechat_window.py --format json 查看细节。",
        )
    try:
        from wechat_ai.app.wechat_window_probe import WeChatWindowProbe

        result = WeChatWindowProbe.from_pyweixin().probe_ui_ready(recent_limit=10).to_dict()
    except Exception as exc:
        return CheckItem(
            id="ui_ready_probe",
            title="UI ready 只读探测",
            status="warn",
            detail=f"窗口控件探测失败：{type(exc).__name__}: {exc}",
            recommendation="确认微信未最小化、当前桌面权限一致，并单独运行 probe_wechat_window.py 查看完整输出。",
        )
    ready = bool(result.get("ready"))
    recommendation = str(result.get("focus_recommendation", "")).strip()
    if not recommendation:
        reason = str(result.get("reason", "")).strip()
        if ready:
            recommendation = "当前窗口探测通过；真实联调前仍建议确认目标会话和输入框焦点。"
        elif reason:
            recommendation = f"窗口探测未就绪：{reason}"
        else:
            recommendation = "窗口探测未就绪；请确认微信主窗口可见、未最小化，并且脚本与微信处于同一交互式桌面。"
    return CheckItem(
        id="ui_ready_probe",
        title="UI ready 只读探测",
        status="ok" if ready else "warn",
        detail=(
            f"ready={result.get('ready')} current_chat={result.get('current_chat', '')!r} "
            f"messages={result.get('visible_message_count', 0)} input_ready={result.get('input_ready')}"
        ),
        recommendation=recommendation,
    )


def build_readiness_report() -> dict[str, object]:
    process_names = _windows_process_names()
    wechat_running = any(name.lower() in process_names for name in WECHAT_PROCESS_NAMES)
    narrator_running = NARRATOR_PROCESS_NAME.lower() in process_names
    existing_paths = _existing_wechat_paths()
    scaling_status, scaling_detail = _display_scaling_detail()
    window_enum_status, window_enum_detail, window_enum_recommendation = _desktop_window_enumeration_detail()

    checks = [
        CheckItem(
            id="wechat_process",
            title="微信进程",
            status="ok" if wechat_running else "warn",
            detail=(
                "检测到微信进程正在运行。"
                if wechat_running
                else "未检测到 WeChat.exe / Weixin.exe；脚本不会自动启动微信。"
            ),
            recommendation="真实联调前请手动登录 Windows 微信客户端，并保持测试账号在线。",
        ),
        CheckItem(
            id="wechat_path",
            title="微信安装路径",
            status="ok" if existing_paths else "manual",
            detail=(
                "检测到候选路径：" + "; ".join(existing_paths)
                if existing_paths
                else "未在常见路径或 WECHAT_PATH / WEIXIN_PATH 中找到微信可执行文件。"
            ),
            recommendation="如安装在自定义目录，请设置 WECHAT_PATH 或在联调记录中写明实际路径。",
        ),
        CheckItem(
            id="narrator_state",
            title="讲述人状态",
            status="warn" if narrator_running else "ok",
            detail=(
                "检测到 Narrator.exe 正在运行。"
                if narrator_running
                else "未检测到 Narrator.exe 正在运行。"
            ),
            recommendation="首启引导可能会临时使用讲述人；真实长跑前建议确认它不会残留干扰焦点。",
        ),
        CheckItem(
            id="desktop_window_enumeration",
            title="桌面窗口枚举",
            status=window_enum_status,
            detail=window_enum_detail,
            recommendation=window_enum_recommendation,
        ),
        _ui_probe_check(wechat_running),
        CheckItem(
            id="display_scaling",
            title="显示缩放",
            status=scaling_status,
            detail=scaling_detail,
            recommendation="真实联调记录需写明显示器数量、主屏分辨率和缩放比例。",
        ),
        CheckItem(
            id="foreground_permissions",
            title="权限与前台窗口",
            status="manual",
            detail="脚本不会提升权限，也不会抢占前台窗口。",
            recommendation="请人工确认微信窗口可见、未被最小化，运行终端和微信处于同一用户桌面会话。",
        ),
    ]

    manual_checklist = [
        ManualChecklistItem(
            id="unread_order",
            title="未读顺序",
            detail="准备至少两个未读会话，观察守护循环是否按预期顺序处理且不会跳过。",
            expected_result="多条未读消息按时间/列表策略稳定处理，并在日志中可追踪。",
        ),
        ManualChecklistItem(
            id="group_sender",
            title="群聊 sender",
            detail="在群聊中由不同成员连续发送消息，检查 sender 识别与身份匹配。",
            expected_result="群成员 sender 不混淆，@ 回复只针对目标消息生成。",
        ),
        ManualChecklistItem(
            id="send_confirmation",
            title="发送确认",
            detail="发送测试回复后，人工确认微信窗口里出现出站消息且没有重复发送。",
            expected_result="本地会话缓存、运行日志和微信 UI 的发送结果一致。",
        ),
        ManualChecklistItem(
            id="focus_recovery",
            title="焦点/最小化恢复",
            detail="将微信最小化或切到其他窗口后继续联调，记录控件定位和恢复行为。",
            expected_result="脚本能明确失败位置，或恢复到可继续处理状态。",
        ),
        ManualChecklistItem(
            id="long_run_observation",
            title="长跑观察",
            detail="按 30 分钟冒烟、2 小时稳定性、8 小时长跑三档记录异常。",
            expected_result="异常可归因到微信窗口、模型、网络、发送确认或数据缓存中的具体环节。",
        ),
    ]

    return {
        "script": "check_wechat_real_run_readiness",
        "safe_to_run_without_wechat": True,
        "does_not_start_or_stop_wechat": True,
        "platform": platform.platform(),
        "checks": [asdict(item) for item in checks],
        "manual_checklist": [asdict(item) for item in manual_checklist],
    }


def _format_text(report: dict[str, object]) -> str:
    lines = [
        "WeChat real-run readiness checklist",
        f"Safe without WeChat: {report['safe_to_run_without_wechat']}",
        f"Platform: {report['platform']}",
        "",
        "Automatic / placeholder checks:",
    ]
    for item in report["checks"]:
        lines.append(f"- [{item['status']}] {item['id']}: {item['title']}")
        lines.append(f"  detail: {item['detail']}")
        lines.append(f"  recommendation: {item['recommendation']}")
    lines.append("")
    lines.append("Manual or follow-up script checklist:")
    for item in report["manual_checklist"]:
        lines.append(f"- {item['id']}: {item['title']}")
        lines.append(f"  detail: {item['detail']}")
        lines.append(f"  expected: {item['expected_result']}")
    return "\n".join(lines)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check readiness for a real WeChat integration run without mutating WeChat state."
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to clear text.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_readiness_report()
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
