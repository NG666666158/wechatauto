from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
