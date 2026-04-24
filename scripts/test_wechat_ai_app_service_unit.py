from __future__ import annotations

import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


def _fresh_dir(prefix: str) -> Path:
    path = TMP_ROOT / prefix.lstrip(".") / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeIdentityAdmin:
    def __init__(self) -> None:
        self.users = [
            {
                "user_id": "user_001",
                "canonical_name": "张先生",
                "status": "confirmed",
                "updated_at": "2026-04-23T13:00:00Z",
                "tags": ["意向客户"],
                "remark": "来自测试桩",
            }
        ]
        self.drafts = [{"draft_user_id": "draft_001"}]
        self.candidates = [{"candidate_id": "candidate_001"}]

    def list_users(self, *, base_dir: Path | None = None) -> list[dict[str, object]]:
        return list(self.users)

    def list_drafts(self, *, base_dir: Path | None = None) -> list[dict[str, object]]:
        return list(self.drafts)

    def list_candidates(self, *, base_dir: Path | None = None) -> list[dict[str, object]]:
        return list(self.candidates)


class FakeDaemonRunner:
    def __init__(self) -> None:
        self.launched: list[dict[str, object]] = []
        self.stopped: list[int] = []
        self.running_pids: set[int] = set()
        self.next_pid = 4321
        self.stop_events: list[object] = []

    def launch(
        self,
        *,
        run_silently: bool = True,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 60.0,
        error_backoff_seconds: float = 5.0,
        stop_event: object | None = None,
    ) -> int:
        pid = self.next_pid
        self.next_pid += 1
        self.running_pids.add(pid)
        self.launched.append(
            {
                "pid": pid,
                "run_silently": run_silently,
                "poll_interval": poll_interval,
                "heartbeat_interval": heartbeat_interval,
                "error_backoff_seconds": error_backoff_seconds,
                "stop_event": stop_event,
            }
        )
        if stop_event is not None:
            self.stop_events.append(stop_event)
        return pid

    def stop(self, pid: int) -> bool:
        self.stopped.append(pid)
        self.running_pids.discard(pid)
        return True

    def is_running(self, pid: int | None) -> bool:
        return pid in self.running_pids


class FakeWebKnowledgeBuilder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build_from_documents(self, file_paths, *, search_limit: int = 5):
        payload = {
            "seed_documents": len(list(file_paths)),
            "search_limit": search_limit,
            "imported_count": 2,
            "index_status": {"ready": True},
        }
        self.calls.append(payload)
        return payload


class FakeReplyPipeline:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def generate_reply(self, message: object) -> str:
        self.messages.append(message)
        return f"建议:{getattr(message, 'text')}"


class FakeReplySender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[dict[str, object]] = []

    def send_reply(self, *, conversation_id: str, text: str, is_group: bool = False) -> dict[str, object]:
        self.sent.append({"conversation_id": conversation_id, "text": text, "is_group": is_group})
        if self.fail:
            raise RuntimeError("wechat send failed")
        return {"sent": True, "message_id": "sent_001"}


class FakeSendConfirmer:
    def __init__(self, *, confirmed: bool = True, fail: bool = False) -> None:
        self.confirmed = confirmed
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def confirm_sent(
        self,
        *,
        conversation_id: str,
        text: str,
        is_group: bool = False,
        send_result: dict[str, object] | None = None,
    ) -> bool:
        self.calls.append(
            {
                "conversation_id": conversation_id,
                "text": text,
                "is_group": is_group,
                "send_result": send_result,
            }
        )
        if self.fail:
            raise RuntimeError("confirmation timed out")
        return self.confirmed


class FakeWindowProbe:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls = 0

    def probe_ui_ready(self):
        self.calls += 1
        return self.result


class DesktopSettingsStoreTests(TestCase):
    def test_load_defaults_when_file_missing(self) -> None:
        from wechat_ai.app.settings_store import DesktopSettingsStore

        temp_dir = _fresh_dir(".tmp_app_service_defaults")
        try:
            store = DesktopSettingsStore(temp_dir / "desktop_settings.json")
            snapshot = store.load()
            self.assertTrue(snapshot.auto_reply_enabled)
            self.assertEqual(snapshot.reply_style, "自然友好")
            self.assertEqual(snapshot.work_hours.start, "09:00")
            self.assertTrue(snapshot.run_silently)
            self.assertEqual(snapshot.esc_action, "pause")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_persists_patch_and_schedule_blocks(self) -> None:
        from wechat_ai.app.settings_store import DesktopSettingsStore

        temp_dir = _fresh_dir(".tmp_app_service_update")
        try:
            store = DesktopSettingsStore(temp_dir / "desktop_settings.json")
            updated = store.update(
                {
                    "auto_reply_enabled": False,
                    "reply_style": "专业友好",
                    "schedule_enabled": True,
                    "schedule_blocks": [
                        {"day_of_week": "mon", "start": "09:00", "end": "18:00", "label": "工作时段"}
                    ],
                }
            )
            self.assertFalse(updated.auto_reply_enabled)
            self.assertEqual(updated.reply_style, "专业友好")
            self.assertTrue(updated.schedule_enabled)
            self.assertEqual(len(updated.schedule_blocks), 1)
            self.assertEqual(updated.schedule_blocks[0].label, "工作时段")
            reloaded = store.load()
            self.assertEqual(reloaded.schedule_blocks[0].day_of_week, "mon")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class AppControlModulesTests(TestCase):
    def test_daemon_controller_tracks_start_heartbeat_and_error(self) -> None:
        from wechat_ai.app.daemon_controller import DaemonController

        temp_dir = _fresh_dir(".tmp_daemon_controller")
        try:
            controller = DaemonController(temp_dir / "daemon_state.json")
            started = controller.start(run_silently=True)
            self.assertEqual(started.state, "running")
            self.assertTrue(started.run_silently)
            heartbeat = controller.record_heartbeat()
            self.assertIsNotNone(heartbeat.last_heartbeat)
            errored = controller.record_error(exception_type="RuntimeError", exception_message="boom", base_backoff_seconds=2.0)
            self.assertEqual(errored.consecutive_errors, 1)
            self.assertEqual(errored.retry_backoff_seconds, 2.0)
            recovered = controller.record_loop_success()
            self.assertEqual(recovered.consecutive_errors, 0)
            self.assertIsNone(recovered.next_retry_at)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_schedule_manager_decides_run_and_pause(self) -> None:
        from wechat_ai.app.models import ScheduleBlock, SettingsSnapshot
        from wechat_ai.app.schedule_manager import ScheduleManager

        manager = ScheduleManager()
        settings = SettingsSnapshot(
            schedule_enabled=True,
            schedule_blocks=[ScheduleBlock(day_of_week="mon", start="09:00", end="18:00", label="工作时段")],
        )
        active = manager.evaluate(settings, now=datetime(2026, 4, 20, 10, 0, 0))
        self.assertTrue(active.should_run)
        self.assertEqual(active.next_action, "pause")
        waiting = manager.evaluate(settings, now=datetime(2026, 4, 20, 20, 0, 0))
        self.assertFalse(waiting.should_run)
        self.assertEqual(waiting.next_action, "start")

    def test_tray_adapter_builds_menu_state(self) -> None:
        from wechat_ai.app.models import DaemonStatus, ScheduleStatus
        from wechat_ai.app.tray_adapter import TrayAdapter

        adapter = TrayAdapter()
        state = adapter.build_state(
            daemon_status=DaemonStatus(state="running"),
            schedule_status=ScheduleStatus(enabled=True, should_run=True, next_action="pause", reason="within_schedule_block"),
        )
        self.assertIn("WeChat AI", state.tooltip)
        self.assertEqual(state.recommended_action, "pause_daemon")
        self.assertGreaterEqual(len(state.menu_items), 4)


class DesktopAppServiceTests(TestCase):
    def test_get_app_status_returns_dashboard_shape(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_status")
        try:
            service = DesktopAppService(data_root=temp_dir, identity_admin_module=FakeIdentityAdmin())
            status = service.get_app_status()
            self.assertIn(status.wechat_status, {"unknown", "connected", "disconnected"})
            self.assertIn(status.daemon_state, {"stopped", "running", "paused"})
            self.assertEqual(status.pending_count, 2)
            self.assertIsInstance(status.auto_reply_enabled, bool)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_settings_round_trip(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_roundtrip")
        try:
            service = DesktopAppService(data_root=temp_dir)
            updated = service.update_settings({"reply_style": "专业友好"})
            self.assertEqual(updated.reply_style, "专业友好")
            self.assertEqual(service.get_settings().reply_style, "专业友好")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_message_placeholders_are_structured(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_placeholder")
        try:
            service = DesktopAppService(data_root=temp_dir)
            result = service.send_reply("friend:alice", "你好")
            self.assertEqual(result["status"], "not_implemented")
            self.assertEqual(result["action"], "send_reply")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_conversation_store_and_suggestion_pipeline_are_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_conversations")
        try:
            pipeline = FakeReplyPipeline()
            service = DesktopAppService(data_root=temp_dir, reply_pipeline=pipeline)
            service.record_conversation_message(
                "friend:alice",
                sender="Alice",
                text="请问支持试用吗？",
                direction="incoming",
            )
            service.record_conversation_message(
                "friend:alice",
                sender="assistant",
                text="支持 7 天试用。",
                direction="outgoing",
            )

            conversations = service.list_conversations()
            detail = service.get_conversation("friend:alice")
            suggestion = service.suggest_reply("friend:alice", "请问支持试用吗？")

            self.assertEqual(conversations[0].conversation_id, "friend:alice")
            self.assertEqual(conversations[0].latest_message, "支持 7 天试用。")
            self.assertEqual(detail["conversation"]["title"], "Alice")
            self.assertEqual(len(detail["messages"]), 2)
            self.assertEqual(suggestion.status, "ready")
            self.assertEqual(suggestion.suggestion, "建议:请问支持试用吗？")
            self.assertEqual(getattr(pipeline.messages[0], "conversation_id"), "friend:alice")
            self.assertEqual(getattr(pipeline.messages[0], "chat_type"), "friend")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_preflight_blocks_unsafe_conversation_states(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_preflight")
        try:
            service = DesktopAppService(data_root=temp_dir)

            empty = service.send_reply("friend:alice", "   ")
            self.assertEqual(empty["status"], "blocked")
            self.assertEqual(empty["reason_code"], "EMPTY_TEXT")

            service.update_conversation_control("friend:alice", {"human_takeover": True})
            takeover = service.send_reply("friend:alice", "你好")
            self.assertEqual(takeover["status"], "blocked")
            self.assertEqual(takeover["reason_code"], "HUMAN_TAKEOVER")

            service.update_conversation_control("friend:alice", {"human_takeover": False, "paused": True})
            paused = service.send_reply("friend:alice", "你好")
            self.assertEqual(paused["reason_code"], "CONVERSATION_PAUSED")

            service.update_conversation_control("friend:alice", {"paused": False, "blacklisted": True})
            blacklisted = service.send_reply("friend:alice", "你好")
            self.assertEqual(blacklisted["reason_code"], "BLACKLISTED")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_preflight_passes_before_real_sender_is_connected(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_preflight_allowed")
        try:
            service = DesktopAppService(data_root=temp_dir)
            service.record_conversation_message("friend:alice", sender="Alice", text="你好", direction="incoming")

            result = service.send_reply("friend:alice", "您好，支持试用。")

            self.assertEqual(result["status"], "not_implemented")
            self.assertTrue(result["allowed"])
            self.assertEqual(result["conversation_id"], "friend:alice")
            self.assertEqual(result["text"], "您好，支持试用。")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_calls_sender_and_records_outgoing_message(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_real")
        try:
            sender = FakeReplySender()
            service = DesktopAppService(data_root=temp_dir, reply_sender=sender)
            service.record_conversation_message("friend:alice", sender="Alice", text="你好", direction="incoming")

            result = service.send_reply("friend:alice", "您好，支持试用。")
            detail = service.get_conversation("friend:alice")

            self.assertEqual(result["status"], "sent")
            self.assertTrue(result["allowed"])
            self.assertEqual(sender.sent, [{"conversation_id": "friend:alice", "text": "您好，支持试用。", "is_group": False}])
            self.assertEqual(detail["messages"][-1]["direction"], "outgoing")
            self.assertEqual(detail["messages"][-1]["text"], "您好，支持试用。")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_confirms_sent_message_before_recording_outgoing_message(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_confirmed")
        try:
            sender = FakeReplySender()
            confirmer = FakeSendConfirmer()
            service = DesktopAppService(data_root=temp_dir, reply_sender=sender, send_confirmer=confirmer)
            service.record_conversation_message("group:support", sender="Support", text="hello", direction="incoming")

            result = service.send_reply("group:support", " confirmed reply ")
            detail = service.get_conversation("group:support")

            self.assertEqual(result["status"], "sent")
            self.assertTrue(result["confirmed"])
            self.assertEqual(result["send_result"], {"sent": True, "message_id": "sent_001"})
            self.assertEqual(
                confirmer.calls,
                [
                    {
                        "conversation_id": "group:support",
                        "text": "confirmed reply",
                        "is_group": True,
                        "send_result": {"sent": True, "message_id": "sent_001"},
                    }
                ],
            )
            self.assertEqual(detail["messages"][-1]["direction"], "outgoing")
            self.assertEqual(detail["messages"][-1]["text"], "confirmed reply")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_reports_unconfirmed_without_recording_outgoing_message(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_unconfirmed")
        try:
            sender = FakeReplySender()
            confirmer = FakeSendConfirmer(confirmed=False)
            service = DesktopAppService(data_root=temp_dir, reply_sender=sender, send_confirmer=confirmer)
            service.record_conversation_message("friend:alice", sender="Alice", text="hello", direction="incoming")

            result = service.send_reply("friend:alice", "not visible yet")
            detail = service.get_conversation("friend:alice")

            self.assertEqual(result["status"], "unconfirmed")
            self.assertFalse(result["confirmed"])
            self.assertEqual(result["reason_code"], "SEND_NOT_CONFIRMED")
            self.assertEqual(result["send_result"], {"sent": True, "message_id": "sent_001"})
            self.assertEqual(len(detail["messages"]), 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_send_reply_reports_sender_failure_without_recording_outgoing_message(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_send_failure")
        try:
            service = DesktopAppService(data_root=temp_dir, reply_sender=FakeReplySender(fail=True))
            service.record_conversation_message("friend:alice", sender="Alice", text="你好", direction="incoming")

            result = service.send_reply("friend:alice", "您好")
            detail = service.get_conversation("friend:alice")

            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["sent"])
            self.assertEqual(result["reason_code"], "SEND_FAILED")
            self.assertEqual(len(detail["messages"]), 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_self_identity_crud_and_preview_are_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_self_identity")
        try:
            service = DesktopAppService(data_root=temp_dir)
            global_profile = service.update_global_self_identity({"display_name": "碱水", "identity_facts": ["我是产品负责人"]})
            relationship = service.update_relationship_self_identity_profile(
                "teacher",
                {"identity_facts": ["我是 2023 级学生"], "trigger_tags": ["老师"]},
            )
            override = service.update_user_self_identity_override(
                "user_001",
                {"relationship_override": "teacher", "identity_facts": ["我是 3 班班长"]},
            )
            preview = service.preview_self_identity("user_001", tags=["朋友"])

            self.assertEqual(global_profile["display_name"], "碱水")
            self.assertEqual(relationship["relationship"], "teacher")
            self.assertEqual(override["user_id"], "user_001")
            self.assertEqual(preview["relationship"], "teacher")
            self.assertIn("我是 3 班班长", preview["identity_facts"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_knowledge_status_shape_is_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_knowledge_status")
        try:
            service = DesktopAppService(data_root=temp_dir)
            status = service.get_knowledge_status()
            self.assertIn("ready", status)
            self.assertIn("index_path", status)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_daemon_state_transitions_are_persisted(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_daemon")
        try:
            runner = FakeDaemonRunner()
            service = DesktopAppService(data_root=temp_dir, daemon_runner=runner)
            started = service.start_daemon()
            self.assertEqual(started["state"], "running")
            self.assertEqual(started["pid"], 4321)
            self.assertEqual(service.pause_daemon()["state"], "paused")
            self.assertEqual(runner.stopped, [4321])
            self.assertEqual(service.stop_daemon()["state"], "stopped")
            self.assertEqual(service.get_app_status().daemon_state, "stopped")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_stop_daemon_sets_stop_event_before_stopping_runner(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_stop_event")
        try:
            runner = FakeDaemonRunner()
            service = DesktopAppService(data_root=temp_dir, daemon_runner=runner)
            service.start_daemon()

            self.assertEqual(len(runner.stop_events), 1)
            stop_event = runner.stop_events[0]
            self.assertFalse(stop_event.is_set())

            stopped = service.stop_daemon()

            self.assertTrue(stop_event.is_set())
            self.assertEqual(stopped["state"], "stopped")
            self.assertEqual(runner.stopped, [4321])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_daemon_status_normalizes_dead_process(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_dead_daemon")
        try:
            runner = FakeDaemonRunner()
            service = DesktopAppService(data_root=temp_dir, daemon_runner=runner)
            started = service.start_daemon()
            runner.running_pids.clear()
            status = service.get_daemon_status()
            self.assertEqual(started["state"], "running")
            self.assertEqual(status["state"], "stopped")
            self.assertIsNone(status["pid"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_import_knowledge_files_returns_service_shape(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_import")
        try:
            source = temp_dir / "faq.txt"
            source.write_text("支持试用 7 天。", encoding="utf-8")
            service = DesktopAppService(data_root=temp_dir)
            payload = service.import_knowledge_files([source])
            self.assertTrue(payload["index_rebuilt"])
            self.assertEqual(payload["files"][0]["status"], "imported")
            self.assertIn("ready", payload["index_status"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_search_knowledge_returns_retrieved_chunks(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_search")
        try:
            source = temp_dir / "refund.txt"
            source.write_text("退款说明：支持7天内申请退款，审核通过后原路退回。", encoding="utf-8")
            service = DesktopAppService(data_root=temp_dir)
            service.import_knowledge_files([source])
            results = service.search_knowledge("怎么申请退款", limit=2)
            self.assertEqual(len(results), 1)
            self.assertIn("退款说明", results[0]["text"])
            self.assertIn("metadata", results[0])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recent_logs_privacy_policy_and_environment_are_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_ops")
        try:
            service = DesktopAppService(data_root=temp_dir)
            service.runtime_log_path.write_text(
                '{"event_type":"heartbeat","message":"api_key=secret-value"}\n',
                encoding="utf-8",
            )

            logs = service.get_recent_logs(limit=5)
            privacy = service.get_privacy_policy()
            updated = service.update_privacy_policy({"log_retention_days": 7})
            environment = service.get_wechat_environment_status()

            self.assertEqual(logs[0]["event_type"], "heartbeat")
            self.assertIn("[redacted]", logs[0]["message"])
            self.assertTrue(privacy["redact_sensitive_logs"])
            self.assertEqual(updated["log_retention_days"], 7)
            self.assertIn("wechat_running", environment)
            self.assertIn("ui_ready", environment)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_environment_status_includes_read_only_wechat_window_probe(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_ui_probe")
        try:
            probe = FakeWindowProbe(
                {
                    "ready": True,
                    "status": "ok",
                    "current_chat": "张先生",
                    "visible_message_count": 3,
                    "latest_visible_text": "最新消息",
                }
            )
            service = DesktopAppService(data_root=temp_dir, wechat_window_probe=probe)

            environment = service.get_wechat_environment_status()

            self.assertEqual(environment["ui_ready"], True)
            self.assertEqual(environment["ui_probe"]["current_chat"], "张先生")
            self.assertEqual(environment["ui_probe"]["visible_message_count"], 3)
            self.assertEqual(probe.calls, 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_conversation_control_and_retention_policy_are_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_controls")
        try:
            service = DesktopAppService(data_root=temp_dir)
            control = service.update_conversation_control(
                "user_001",
                {
                    "human_takeover": True,
                    "paused": True,
                    "blacklisted": True,
                },
            )
            settings = service.get_settings()
            service.runtime_log_path.write_text(
                "\n".join(
                    [
                        '{"timestamp":"2000-01-01T00:00:00Z","event_type":"old"}',
                        '{"timestamp":"2999-01-01T00:00:00Z","event_type":"new"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            cleanup = service.apply_retention_policy()
            logs = service.get_recent_logs(limit=10)

            self.assertTrue(control["human_takeover"])
            self.assertTrue(control["paused"])
            self.assertTrue(control["blacklisted"])
            self.assertIn("user_001", settings.human_takeover_sessions)
            self.assertIn("user_001", settings.paused_sessions)
            self.assertIn("user_001", settings.blacklist)
            self.assertGreaterEqual(cleanup["logs_removed"], 1)
            self.assertEqual([event["event_type"] for event in logs], ["new"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_build_web_knowledge_from_documents_delegates_to_builder(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_web_builder")
        try:
            fake_builder = FakeWebKnowledgeBuilder()
            seed = temp_dir / "seed.md"
            seed.write_text("# 智能客服\n", encoding="utf-8")
            service = DesktopAppService(data_root=temp_dir, web_knowledge_builder=fake_builder)
            payload = service.build_web_knowledge_from_documents([seed], search_limit=3)
            self.assertEqual(payload["seed_documents"], 1)
            self.assertEqual(payload["search_limit"], 3)
            self.assertEqual(fake_builder.calls[0]["imported_count"], 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_customer_views_use_identity_admin_data(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_customers")
        try:
            service = DesktopAppService(data_root=temp_dir, identity_admin_module=FakeIdentityAdmin())
            customers = service.list_customers()
            self.assertEqual(len(customers), 1)
            self.assertEqual(customers[0].display_name, "张先生")
            detail = service.get_customer("user_001")
            self.assertEqual(detail["display_name"], "张先生")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_schedule_tick_can_start_and_pause_daemon(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_schedule")
        try:
            service = DesktopAppService(data_root=temp_dir)
            service.update_settings(
                {
                    "schedule_enabled": True,
                    "schedule_blocks": [
                        {"day_of_week": "mon", "start": "09:00", "end": "18:00", "label": "工作时段"}
                    ],
                }
            )
            started = service.apply_schedule_tick(now=datetime(2026, 4, 20, 10, 0, 0))
            self.assertEqual(started["action"], "start")
            paused = service.apply_schedule_tick(now=datetime(2026, 4, 20, 20, 0, 0))
            self.assertEqual(paused["action"], "pause")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tray_state_is_available(self) -> None:
        from wechat_ai.app.service import DesktopAppService

        temp_dir = _fresh_dir(".tmp_app_service_tray")
        try:
            service = DesktopAppService(data_root=temp_dir)
            tray_state = service.get_tray_state(now=datetime(2026, 4, 20, 10, 0, 0))
            self.assertIn("tooltip", tray_state)
            self.assertIn("menu_items", tray_state)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
