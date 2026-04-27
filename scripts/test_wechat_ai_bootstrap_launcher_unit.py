from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class WeChatBootstrapperTests(unittest.TestCase):
    def test_bootstrap_starts_wechat_then_narrator_then_guardian_and_stops_narrator(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        launched: list[tuple[str, ...]] = []
        ran_guardian: list[tuple[str, ...]] = []
        stopped: list[str] = []
        sleeps: list[float] = []
        narrator_running = {"value": False}

        def launch_process(command):
            if isinstance(command, str):
                launched.append((command,))
            else:
                launched.append(tuple(command))
            if launched[-1][0].lower().endswith("narrator.exe"):
                narrator_running["value"] = True
            return object()

        def ui_ready_check():
            return None

        def sleep(seconds: float) -> None:
            sleeps.append(seconds)

        def stop_process(name: str) -> None:
            stopped.append(name)
            if name.lower() == "narrator.exe":
                narrator_running["value"] = False

        def run_guardian(command):
            ran_guardian.append(tuple(command))
            return 0

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=ui_ready_check,
            launch_process=launch_process,
            run_guardian=run_guardian,
            sleep=sleep,
            stop_process=stop_process,
            is_process_running_fn=lambda name: narrator_running["value"] if name.lower() == "narrator.exe" else False,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: False,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                ready_timeout_seconds=30.0,
                ready_poll_interval_seconds=2.0,
                narrator_settle_seconds=5.0,
                guardian_command=("py", "scripts/run_minimax_global_auto_reply.py", "--forever", "--debug"),
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(launched[0], (r"C:\Weixin\Weixin.exe",))
        self.assertTrue(launched[1][0].lower().endswith("narrator.exe"))
        self.assertEqual(
            ran_guardian[0],
            ("py", "scripts/run_minimax_global_auto_reply.py", "--forever", "--debug"),
        )
        self.assertEqual(stopped, ["Narrator.exe"])
        self.assertEqual(sleeps, [5.0])
        self.assertFalse(result.ui_ready)
        self.assertEqual(result.guardian_exit_code, 0)

    def test_bootstrap_times_out_without_starting_guardian(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        launched: list[tuple[str, ...]] = []
        fake_now = {"value": 0.0}

        def launch_process(command):
            launched.append(tuple(command) if not isinstance(command, str) else (command,))
            return object()

        def sleep(seconds: float) -> None:
            fake_now["value"] += seconds

        def fake_time() -> float:
            return fake_now["value"]

        import wechat_ai.app.wechat_bootstrap as module

        original_time = module.time.time
        module.time.time = fake_time
        try:
            bootstrapper = WeChatFirstRunBootstrapper(
                ui_ready_check=lambda: None,
                launch_process=launch_process,
                sleep=sleep,
                stop_process=lambda name: None,
                is_process_running_fn=lambda name: False,
                locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
                is_wechat_running=lambda: False,
            )
            result = bootstrapper.run(
                BootstrapSettings(
                    ready_timeout_seconds=4.0,
                    ready_poll_interval_seconds=2.0,
                    narrator_settle_seconds=0.0,
                    start_guardian=False,
                    guardian_command=("py", "scripts/run_minimax_global_auto_reply.py", "--forever", "--debug"),
                )
            )
        finally:
            module.time.time = original_time

        self.assertFalse(result.ok)
        self.assertFalse(result.guardian_started)
        self.assertEqual(
            launched,
            [
                (r"C:\Weixin\Weixin.exe",),
                (module.default_narrator_path(),),
            ],
        )

    def test_wait_for_ui_ready_does_not_relax_to_running_wechat(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        fake_now = {"value": 0.0}

        def sleep(seconds: float) -> None:
            fake_now["value"] += seconds

        def fake_time() -> float:
            return fake_now["value"]

        import wechat_ai.app.wechat_bootstrap as module

        original_time = module.time.time
        module.time.time = fake_time
        try:
            bootstrapper = WeChatFirstRunBootstrapper(
                ui_ready_check=lambda: None,
                launch_process=lambda command: object(),
                sleep=sleep,
                stop_process=lambda name: None,
                is_process_running_fn=lambda name: False,
                locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
                is_wechat_running=lambda: True,
            )
            result = bootstrapper.run(
                BootstrapSettings(
                    ready_timeout_seconds=4.0,
                    ready_poll_interval_seconds=2.0,
                    narrator_settle_seconds=0.0,
                    wait_for_ui_ready_before_guardian=True,
                    guardian_command=("py", "scripts/run_minimax_global_auto_reply.py", "--forever", "--debug"),
                )
            )
        finally:
            module.time.time = original_time

        self.assertFalse(result.ok)
        self.assertFalse(result.ui_ready)
        self.assertFalse(result.guardian_started)

    def test_running_wechat_does_not_launch_exe_again_before_detection(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        launched: list[tuple[str, ...]] = []
        statuses: list[str] = []

        def launch_process(command):
            launched.append(tuple(command) if not isinstance(command, str) else (command,))
            return object()

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=lambda: {"ready": True},
            launch_process=launch_process,
            sleep=lambda seconds: None,
            stop_process=lambda name: None,
            is_process_running_fn=lambda name: True if name.lower() == "narrator.exe" else False,
            status_callback=statuses.append,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: True,
            is_wechat_window_available=lambda: True,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                ready_timeout_seconds=2.0,
                ready_poll_interval_seconds=1.0,
                narrator_settle_seconds=0.0,
                start_guardian=False,
                wait_for_ui_ready_before_guardian=True,
            )
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.ui_ready)
        self.assertEqual(launched, [])
        self.assertTrue(any("不重复启动微信" in message for message in statuses))

    def test_running_ready_wechat_skips_narrator_start(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        launched: list[tuple[str, ...]] = []
        statuses: list[str] = []

        def launch_process(command):
            launched.append(tuple(command) if not isinstance(command, str) else (command,))
            return object()

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=lambda: {"ready": True},
            launch_process=launch_process,
            sleep=lambda seconds: None,
            stop_process=lambda name: None,
            is_process_running_fn=lambda name: False,
            status_callback=statuses.append,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: True,
            is_wechat_window_available=lambda: True,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                ready_timeout_seconds=2.0,
                ready_poll_interval_seconds=1.0,
                narrator_settle_seconds=0.0,
                start_guardian=False,
                wait_for_ui_ready_before_guardian=True,
            )
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.ui_ready)
        self.assertFalse(result.narrator_started)
        self.assertFalse(result.narrator_stopped)
        self.assertEqual(launched, [])
        self.assertTrue(any("先检测现有微信主界面" in message for message in statuses))
        self.assertFalse(any("启动讲述人" in message for message in statuses))
        self.assertFalse(any("关闭讲述人" in message for message in statuses))

    def test_running_wechat_without_window_launches_exe_once_to_show_login(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        launched: list[tuple[str, ...]] = []
        statuses: list[str] = []

        def launch_process(command):
            launched.append(tuple(command) if not isinstance(command, str) else (command,))
            return object()

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=lambda: {"ready": True},
            launch_process=launch_process,
            sleep=lambda seconds: None,
            stop_process=lambda name: None,
            is_process_running_fn=lambda name: True if name.lower() == "narrator.exe" else False,
            status_callback=statuses.append,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: True,
            is_wechat_window_available=lambda: False,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                ready_timeout_seconds=2.0,
                ready_poll_interval_seconds=1.0,
                narrator_settle_seconds=0.0,
                start_guardian=False,
                wait_for_ui_ready_before_guardian=True,
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(launched, [(r"C:\Weixin\Weixin.exe",)])
        self.assertTrue(any("没有可识别窗口" in message for message in statuses))

    def test_first_run_script_marks_pyweixin_checks_as_ready(self) -> None:
        import scripts.bootstrap_wechat_first_run as script

        fake_window = SimpleNamespace(handle=123, class_name=lambda: "mmui::MainWindow")
        original_open_weixin = script.Navigator.open_weixin
        script.Navigator.open_weixin = lambda **kwargs: fake_window  # type: ignore[method-assign]
        try:
            result = script._ui_ready_check()
        finally:
            script.Navigator.open_weixin = original_open_weixin  # type: ignore[method-assign]

        self.assertTrue(result["ready"])
        self.assertEqual(result["checks"]["main_window"]["class_name"], "mmui::MainWindow")

    def test_first_run_script_resets_pyweixin_window_cache_before_detection(self) -> None:
        import scripts.bootstrap_wechat_first_run as script

        original_open_weixin = script.Navigator.open_weixin
        fake_window = SimpleNamespace(handle=123, class_name=lambda: "mmui::MainWindow")

        def fake_open_weixin(**kwargs):
            self.assertEqual(script.wx.hwnd, 0)
            self.assertEqual(script.wx.possible_windows, [])
            self.assertEqual(script.wx.window_type, 1)
            return fake_window

        script.wx.hwnd = 456
        script.wx.possible_windows = [456]
        script.wx.window_type = 0
        script.Navigator.open_weixin = fake_open_weixin  # type: ignore[method-assign]
        try:
            result = script._ui_ready_check()
        finally:
            script.Navigator.open_weixin = original_open_weixin  # type: ignore[method-assign]

        self.assertTrue(result["ready"])

    def test_first_run_script_keeps_waiting_when_open_weixin_is_not_ready(self) -> None:
        import scripts.bootstrap_wechat_first_run as script

        original_open_weixin = script.Navigator.open_weixin
        script.Navigator.open_weixin = lambda **kwargs: (_ for _ in ()).throw(script.NotLoginError())  # type: ignore[method-assign]
        try:
            result = script._ui_ready_check()
        finally:
            script.Navigator.open_weixin = original_open_weixin  # type: ignore[method-assign]

        self.assertFalse(result["ready"])
        self.assertEqual(result["checks"]["state"], "NotLoginError")

    def test_first_run_script_wechat_path_falls_back_when_pyweixin_detection_fails(self) -> None:
        import scripts.bootstrap_wechat_first_run as script

        original_where_weixin = script.Tools.where_weixin
        script.Tools.where_weixin = lambda **kwargs: ""  # type: ignore[method-assign]
        try:
            self.assertEqual(script._locate_wechat_path(), r"C:\Weixin\Weixin.exe")
        finally:
            script.Tools.where_weixin = original_where_weixin  # type: ignore[method-assign]

    def test_ready_false_probe_payload_is_not_treated_as_ready(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        fake_now = {"value": 0.0}

        def sleep(seconds: float) -> None:
            fake_now["value"] += seconds

        def fake_time() -> float:
            return fake_now["value"]

        import wechat_ai.app.wechat_bootstrap as module

        original_time = module.time.time
        module.time.time = fake_time
        try:
            bootstrapper = WeChatFirstRunBootstrapper(
                ui_ready_check=lambda: {"ready": False, "status": "error", "reason": "NotFoundError"},
                launch_process=lambda command: object(),
                sleep=sleep,
                stop_process=lambda name: None,
                is_process_running_fn=lambda name: False,
                locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
                is_wechat_running=lambda: False,
            )
            result = bootstrapper.run(
                BootstrapSettings(
                    ready_timeout_seconds=2.0,
                    ready_poll_interval_seconds=1.0,
                    narrator_settle_seconds=0.0,
                    start_guardian=False,
                    wait_for_ui_ready_before_guardian=True,
                )
            )
        finally:
            module.time.time = original_time

        self.assertFalse(result.ok)
        self.assertFalse(result.ui_ready)
        self.assertEqual(result.attempts, 3)

    def test_auxiliary_probe_payload_without_ready_flag_is_not_treated_as_ready(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        fake_now = {"value": 0.0}

        def sleep(seconds: float) -> None:
            fake_now["value"] += seconds

        def fake_time() -> float:
            return fake_now["value"]

        import wechat_ai.app.wechat_bootstrap as module

        original_time = module.time.time
        module.time.time = fake_time
        try:
            bootstrapper = WeChatFirstRunBootstrapper(
                ui_ready_check=lambda: {"recent_sessions": [{"name": "Alice"}]},
                launch_process=lambda command: object(),
                sleep=sleep,
                stop_process=lambda name: None,
                is_process_running_fn=lambda name: False,
                locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
                is_wechat_running=lambda: False,
            )
            result = bootstrapper.run(
                BootstrapSettings(
                    ready_timeout_seconds=2.0,
                    ready_poll_interval_seconds=1.0,
                    narrator_settle_seconds=0.0,
                    start_guardian=False,
                    wait_for_ui_ready_before_guardian=True,
                )
            )
        finally:
            module.time.time = original_time

        self.assertFalse(result.ok)
        self.assertFalse(result.ui_ready)
        self.assertEqual(result.attempts, 3)

    def test_bootstrap_records_manual_interrupt_from_guardian(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        def run_guardian(command):
            del command
            raise KeyboardInterrupt()

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=lambda: None,
            launch_process=lambda command: object(),
            run_guardian=run_guardian,
            sleep=lambda seconds: None,
            stop_process=lambda name: None,
            is_process_running_fn=lambda name: False,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: False,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                narrator_settle_seconds=0.0,
                guardian_command=("py", "scripts/run_minimax_global_auto_reply.py", "--forever", "--debug"),
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.guardian_exit_code, 130)

    def test_narrator_launch_failure_does_not_crash_relaxed_bootstrap(self) -> None:
        from wechat_ai.app.wechat_bootstrap import BootstrapSettings, WeChatFirstRunBootstrapper

        statuses: list[str] = []

        def launch_process(command):
            command_tuple = tuple(command) if not isinstance(command, str) else (command,)
            if command_tuple[0].lower().endswith("narrator.exe"):
                raise OSError("narrator failed")
            return object()

        bootstrapper = WeChatFirstRunBootstrapper(
            ui_ready_check=lambda: None,
            launch_process=launch_process,
            sleep=lambda seconds: None,
            stop_process=lambda name: None,
            is_process_running_fn=lambda name: False,
            status_callback=statuses.append,
            locate_wechat_path=lambda: r"C:\Weixin\Weixin.exe",
            is_wechat_running=lambda: True,
        )

        result = bootstrapper.run(
            BootstrapSettings(
                narrator_settle_seconds=0.0,
                start_guardian=False,
                wait_for_ui_ready_before_guardian=False,
            )
        )

        self.assertTrue(result.ok)
        self.assertFalse(result.narrator_started)
        self.assertTrue(any("Narrator" in message or "讲述人" in message for message in statuses))

    def test_is_process_running_falls_back_when_tasklist_is_denied(self) -> None:
        import wechat_ai.app.wechat_bootstrap as module

        calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            del kwargs
            calls.append([str(part) for part in command])
            if command[0] == "tasklist":
                return SimpleNamespace(returncode=1, stdout="", stderr="ERROR: Access denied")
            return SimpleNamespace(returncode=0, stdout="Weixin 12276", stderr="")

        original_run = module.subprocess.run
        module.subprocess.run = fake_run
        try:
            self.assertTrue(module.is_process_running("Weixin.exe"))
        finally:
            module.subprocess.run = original_run

        self.assertEqual(calls[0][0], "tasklist")
        self.assertEqual(calls[1][:3], ["powershell", "-NoProfile", "-Command"])
        self.assertTrue(calls[1][3].startswith("Get-Process"))


if __name__ == "__main__":
    unittest.main()
