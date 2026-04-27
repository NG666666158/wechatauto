from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


VK_CODES = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Out-of-process emergency stop watchdog for WeChat AI runtime.")
    parser.add_argument("--target-pid", type=int, required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--hotkey", default="ctrl+shift+f12")
    parser.add_argument("--poll-interval", type=float, default=0.05)
    parser.add_argument("--log-file", default="")
    args = parser.parse_args()

    stop_file = Path(args.stop_file)
    log_file = Path(args.log_file) if args.log_file else None
    hotkey = _parse_hotkey(args.hotkey)
    poll_interval = max(float(args.poll_interval), 0.02)
    armed = False

    _log(log_file, f"watchdog_start target_pid={args.target_pid} hotkey={args.hotkey!r} stop_file={str(stop_file)!r}")
    while _process_alive(args.target_pid):
        reason = ""
        if _stop_file_requested(stop_file):
            reason = "stop_file"
        elif hotkey:
            pressed = _hotkey_pressed(hotkey)
            if pressed and not armed:
                reason = "hotkey"
                armed = True
            elif not pressed:
                armed = False
        if reason:
            _log(log_file, f"watchdog_trigger reason={reason} target_pid={args.target_pid}")
            _kill_process_tree(args.target_pid)
            return 130
        time.sleep(poll_interval)
    _log(log_file, f"watchdog_exit target_gone target_pid={args.target_pid}")
    return 0


def _parse_hotkey(hotkey: str) -> tuple[int, ...]:
    normalized = str(hotkey or "").strip().lower()
    if not normalized or normalized in {"off", "none", "disabled"}:
        return ()
    codes: list[int] = []
    for part in normalized.split("+"):
        name = part.strip()
        if not name:
            continue
        code = VK_CODES.get(name)
        if code is None:
            return ()
        codes.append(code)
    return tuple(codes)


def _hotkey_pressed(codes: tuple[int, ...]) -> bool:
    if not codes or not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        return all(bool(user32.GetAsyncKeyState(code) & 0x8000) for code in codes)
    except Exception:
        return False


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = f"{result.stdout}\n{result.stderr}"
        if str(pid) in output:
            return True
        if result.returncode == 0 and "No tasks" in output:
            return False
        fallback = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; if ($p) {{ 'RUNNING' }}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        return "RUNNING" in str(fallback.stdout)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_process_tree(pid: int) -> None:
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, text=True)
        return
    try:
        os.kill(pid, 9)
    except OSError:
        pass


def _stop_file_requested(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.read_text(encoding="utf-8", errors="ignore").strip())
    except OSError:
        return True


def _log(path: Path | None, message: str) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
