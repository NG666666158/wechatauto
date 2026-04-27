from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


NarratorReadyCheck = Callable[[], object]
LaunchProcess = Callable[[Sequence[str] | str], object]
GuardianRunner = Callable[[Sequence[str]], int | None]
SleepFn = Callable[[float], None]
ProcessStopper = Callable[[str], None]
ProcessRunningCheck = Callable[[str], bool]
StatusCallback = Callable[[str], None]
WeChatPathLocator = Callable[[], str | None]
WeChatRunningCheck = Callable[[], bool]
WeChatWindowAvailableCheck = Callable[[], bool]


@dataclass(slots=True)
class BootstrapSettings:
    ready_timeout_seconds: float = 300.0
    ready_poll_interval_seconds: float = 2.0
    narrator_settle_seconds: float = 5.0
    auto_stop_narrator_on_success: bool = True
    allow_relaxed_ready_when_wechat_running: bool = True
    wait_for_ui_ready_before_guardian: bool = False
    start_guardian: bool = True
    guardian_command: tuple[str, ...] = field(default_factory=tuple)
    wechat_path: str = ""
    narrator_path: str = ""


@dataclass(slots=True)
class BootstrapResult:
    ok: bool
    wechat_started: bool
    narrator_started: bool
    ui_ready: bool
    guardian_started: bool
    narrator_stopped: bool
    attempts: int
    message: str
    guardian_command: tuple[str, ...] = field(default_factory=tuple)
    guardian_exit_code: int | None = None


def default_narrator_path() -> str:
    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    return str(windows_dir / "System32" / "Narrator.exe")


def default_guardian_command(project_root: Path) -> tuple[str, ...]:
    return (
        sys.executable,
        str(project_root / "scripts" / "run_minimax_global_auto_reply.py"),
        "--forever",
        "--debug",
    )


def run_foreground_command(command: Sequence[str]) -> int | None:
    return subprocess.call(list(command))


def popen_launch(command: Sequence[str] | str) -> object:
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    args = command if isinstance(command, str) else list(command)
    try:
        if isinstance(args, str):
            return subprocess.Popen(args, creationflags=creationflags)
        return subprocess.Popen(args, creationflags=creationflags)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 740:
            raise
        if isinstance(args, str):
            os.startfile(args)
            return None
        if len(args) == 1:
            os.startfile(args[0])
            return None
        raise


def stop_process_by_name(process_name: str) -> None:
    subprocess.run(
        ["taskkill", "/IM", process_name, "/F"],
        check=False,
        capture_output=True,
        text=True,
    )


def is_process_running(process_name: str) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process_name.lower() in result.stdout.lower():
        return True
    if result.returncode == 0 and "access denied" not in (result.stderr or "").lower():
        return False
    return _is_process_running_with_powershell(process_name)


def _is_process_running_with_powershell(process_name: str) -> bool:
    process_stem = Path(process_name).stem
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-Process -Name '{process_stem}' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty ProcessName",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return process_stem.lower() in (result.stdout or "").lower()


def locate_existing_wechat_path(candidate: str = "") -> str:
    if candidate:
        return candidate
    env_path = os.environ.get("WECHAT_PATH", "").strip()
    if env_path:
        return env_path
    return r"C:\Weixin\Weixin.exe"


class WeChatFirstRunBootstrapper:
    def __init__(
        self,
        *,
        ui_ready_check: NarratorReadyCheck,
        launch_process: LaunchProcess = popen_launch,
        run_guardian: GuardianRunner = run_foreground_command,
        sleep: SleepFn = time.sleep,
        stop_process: ProcessStopper = stop_process_by_name,
        is_process_running_fn: ProcessRunningCheck = is_process_running,
        status_callback: StatusCallback | None = None,
        locate_wechat_path: WeChatPathLocator | None = None,
        is_wechat_running: WeChatRunningCheck | None = None,
        is_wechat_window_available: WeChatWindowAvailableCheck | None = None,
    ) -> None:
        self.ui_ready_check = ui_ready_check
        self.launch_process = launch_process
        self.run_guardian = run_guardian
        self.sleep = sleep
        self.stop_process = stop_process
        self.is_process_running = is_process_running_fn
        self.status_callback = status_callback or (lambda message: None)
        self.locate_wechat_path = locate_wechat_path or (lambda: locate_existing_wechat_path(""))
        self.is_wechat_running = is_wechat_running or (lambda: False)
        self.is_wechat_window_available = is_wechat_window_available or (lambda: True)

    def run(self, settings: BootstrapSettings) -> BootstrapResult:
        wechat_path = settings.wechat_path.strip() or self._safe_locate_wechat_path()
        narrator_path = settings.narrator_path.strip() or default_narrator_path()
        guardian_command = settings.guardian_command or ()

        wechat_started = False
        narrator_started = False
        guardian_started = False
        narrator_stopped = False

        wechat_already_running = self.is_wechat_running()
        if not wechat_already_running:
            if not wechat_path:
                return BootstrapResult(
                    ok=False,
                    wechat_started=False,
                    narrator_started=False,
                    ui_ready=False,
                    guardian_started=False,
                    narrator_stopped=False,
                    attempts=0,
                    message="未找到微信安装路径，无法自动启动微信。",
                    guardian_command=guardian_command,
                )
            self.status_callback(f"启动微信: {wechat_path}")
            self.launch_process([wechat_path])
            wechat_started = True
        else:
            if self._safe_is_wechat_window_available():
                self.status_callback("检测到微信已在运行，先复用现有窗口检测，不重复启动微信。")
            elif wechat_path:
                self.status_callback("检测到微信进程但没有可识别窗口，启动一次微信显示登录或主窗口。")
                try:
                    self.launch_process([wechat_path])
                    self.status_callback("已请求微信显示窗口。")
                except OSError as exc:
                    self.status_callback(f"拉起微信窗口失败，继续检测现有状态: {exc}")
            else:
                self.status_callback("检测到微信进程但没有可识别窗口，且未找到微信路径，继续等待。")

        attempts = 0
        if wechat_already_running:
            attempts += 1
            self.status_callback(f"先检测现有微信主界面，第 {attempts} 次检测...")
            if self._ui_is_ready():
                return self._finish_success(
                    settings=settings,
                    guardian_command=guardian_command,
                    wechat_started=wechat_started,
                    narrator_started=narrator_started,
                    guardian_started=guardian_started,
                    narrator_stopped=narrator_stopped,
                    attempts=attempts,
                    ui_ready=True,
                    message="微信主界面已识别，未启动讲述人。",
                )

        if not self.is_process_running("Narrator.exe"):
            self.status_callback(f"启动讲述人: {narrator_path}")
            try:
                self.launch_process([narrator_path])
                narrator_started = True
            except OSError as exc:
                self.status_callback(f"Narrator launch failed, continue with existing WeChat UI state: {exc}")
        else:
            self.status_callback("检测到讲述人已在运行，跳过自动启动。")

        if settings.narrator_settle_seconds > 0:
            self.status_callback(f"等待讲述人接管 UI: {settings.narrator_settle_seconds:.1f}s")
            self.sleep(settings.narrator_settle_seconds)

        if settings.start_guardian and guardian_command and not settings.wait_for_ui_ready_before_guardian:
            self.status_callback("跳过独立主界面预检，直接启动正式监听脚本，由监听脚本自行等待微信 UI 就绪。")
            return self._finish_success(
                settings=settings,
                guardian_command=guardian_command,
                wechat_started=wechat_started,
                narrator_started=narrator_started,
                guardian_started=guardian_started,
                narrator_stopped=narrator_stopped,
                attempts=0,
                ui_ready=False,
                message="已启动正式监听脚本，后续由监听脚本自行处理微信界面就绪与重试。",
            )

        deadline = time.time() + max(settings.ready_timeout_seconds, 0.0)
        while True:
            attempts += 1
            self.status_callback(f"等待微信主界面可识别，第 {attempts} 次检测...")
            if self._ui_is_ready():
                return self._finish_success(
                    settings=settings,
                    guardian_command=guardian_command,
                    wechat_started=wechat_started,
                    narrator_started=narrator_started,
                    guardian_started=guardian_started,
                    narrator_stopped=narrator_stopped,
                    attempts=attempts,
                    ui_ready=True,
                    message="微信主界面已识别，守护脚本已启动。",
                )
            if (
                settings.allow_relaxed_ready_when_wechat_running
                and not settings.wait_for_ui_ready_before_guardian
                and attempts >= 1
                and self.is_wechat_running()
            ):
                self.status_callback("未拿到完整主界面信号，但检测到微信已运行，按宽松模式直接启动守护。")
                return self._finish_success(
                    settings=settings,
                    guardian_command=guardian_command,
                    wechat_started=wechat_started,
                    narrator_started=narrator_started,
                    guardian_started=guardian_started,
                    narrator_stopped=narrator_stopped,
                    attempts=attempts,
                    ui_ready=False,
                    message="未拿到完整主界面信号，但已按宽松模式启动守护脚本。",
                )
            if time.time() >= deadline:
                self.status_callback("等待超时，未识别到微信主界面。")
                return BootstrapResult(
                    ok=False,
                    wechat_started=wechat_started,
                    narrator_started=narrator_started,
                    ui_ready=False,
                    guardian_started=False,
                    narrator_stopped=False,
                    attempts=attempts,
                    message="在设定时间内未识别到微信主界面，请确认已扫码登录且讲述人已正常工作。",
                    guardian_command=guardian_command,
                )
            self.sleep(settings.ready_poll_interval_seconds)

    def _finish_success(
        self,
        *,
        settings: BootstrapSettings,
        guardian_command: tuple[str, ...],
        wechat_started: bool,
        narrator_started: bool,
        guardian_started: bool,
        narrator_stopped: bool,
        attempts: int,
        ui_ready: bool,
        message: str,
    ) -> BootstrapResult:
        if settings.auto_stop_narrator_on_success and narrator_started and self.is_process_running("Narrator.exe"):
            self.status_callback("关闭讲述人。")
            self.stop_process("Narrator.exe")
            narrator_stopped = True
        guardian_exit_code = None
        if settings.start_guardian and guardian_command:
            self.status_callback(f"启动守护脚本(前台): {' '.join(guardian_command)}")
            guardian_started = True
            try:
                guardian_exit_code = self.run_guardian(list(guardian_command))
            except KeyboardInterrupt:
                self.status_callback("守护脚本已被手动中断。")
                guardian_exit_code = 130
        return BootstrapResult(
            ok=True,
            wechat_started=wechat_started,
            narrator_started=narrator_started,
            ui_ready=ui_ready,
            guardian_started=guardian_started,
            narrator_stopped=narrator_stopped,
            attempts=attempts,
            message=message,
            guardian_command=guardian_command,
            guardian_exit_code=guardian_exit_code,
        )

    def _ui_is_ready(self) -> bool:
        try:
            value = self.ui_ready_check()
        except Exception:
            return False
        if isinstance(value, dict):
            if "ready" in value:
                return bool(value.get("ready"))
            if "ui_ready" in value:
                return bool(value.get("ui_ready"))
            return False
        if isinstance(value, list):
            return True
        return value is not None

    def _safe_locate_wechat_path(self) -> str:
        try:
            return str(self.locate_wechat_path() or "").strip()
        except Exception:
            return ""

    def _safe_is_wechat_window_available(self) -> bool:
        try:
            return bool(self.is_wechat_window_available())
        except Exception:
            return False


def parse_guardian_command(raw_value: str, project_root: Path) -> tuple[str, ...]:
    cleaned = raw_value.strip()
    if cleaned:
        return tuple(shlex.split(cleaned, posix=False))
    return default_guardian_command(project_root)
