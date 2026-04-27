from __future__ import annotations

import asyncio
from dataclasses import dataclass
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@dataclass(slots=True)
class FakeAppStatus:
    daemon_state: str = "stopped"
    auto_reply_enabled: bool = True
    last_heartbeat: str | None = None


class FakeDesktopService:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.daemon_state: dict[str, object] = {"state": "stopped", "pid": None}
        self.settings: dict[str, object] = {
            "auto_reply_enabled": True,
            "reply_style": "自然友好",
            "work_hours": {"enabled": True, "start": "09:00", "end": "18:00"},
            "privacy": {
                "redact_sensitive_logs": True,
                "log_retention_days": 14,
                "memory_retention_days": 90,
                "max_recent_log_events": 100,
            },
            "human_takeover_sessions": [],
            "paused_sessions": [],
            "whitelist": [],
            "blacklist": [],
        }
        self.log_events: list[dict[str, object]] = [
            {
                "timestamp": "2026-04-24T10:00:00Z",
                "event_type": "heartbeat",
                "trace_id": "trace-ok",
                "message": "token=[redacted]",
            },
            {
                "timestamp": "2026-04-24T10:01:00Z",
                "event_type": "reply.generated",
                "trace_id": "trace-reply",
                "message": "ready",
            },
            {
                "timestamp": "2026-04-24T10:02:00Z",
                "event_type": "reply.error",
                "trace_id": "trace-error",
                "exception_type": "RuntimeError",
            },
            {
                "timestamp": "2026-04-24T10:03:00Z",
                "event_type": "send.blocked",
                "trace_id": "trace-blocked",
                "reason_code": "EMPTY_TEXT",
            },
        ]
        self.environment_status: dict[str, object] = {
            "wechat_running": True,
            "narrator_required": False,
            "ui_ready": "unknown",
            "ui_probe": {
                "window_ready": True,
                "window_minimized": False,
                "input_ready": True,
                "current_chat": "文件传输助手",
            },
        }
        self.recent_logs_calls = 0
        self.environment_calls = 0
        self.bootstrap_calls = 0
        self.last_bootstrap_request: dict[str, object] = {}
        self.bootstrap_result: dict[str, object] = {
            "ok": True,
            "wechat_started": True,
            "narrator_started": True,
            "ui_ready": False,
            "guardian_started": False,
            "narrator_stopped": True,
            "attempts": 1,
            "message": "已完成首次启动引导，准备启动守护。",
            "guardian_command": [],
            "guardian_exit_code": None,
            "status_lines": ["启动微信: C:\\Weixin\\Weixin.exe", "检测到微信已运行，按宽松模式继续启动守护。"],
            "environment": {
                "wechat_running": True,
                "narrator_required": True,
                "ui_ready": False,
            },
        }

    def get_app_status(self) -> FakeAppStatus:
        return FakeAppStatus(daemon_state=str(self.daemon_state["state"]))

    def get_daemon_status(self) -> dict[str, object]:
        return dict(self.daemon_state)

    def start_daemon(self) -> dict[str, object]:
        self.started += 1
        self.daemon_state = {"state": "running", "pid": 4321}
        return dict(self.daemon_state)

    def stop_daemon(self) -> dict[str, object]:
        self.stopped += 1
        self.daemon_state = {"state": "stopped", "pid": None}
        return dict(self.daemon_state)

    def bootstrap_wechat_for_web_start(
        self,
        *,
        ready_timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 1.0,
        narrator_settle_seconds: float = 10.0,
        wait_for_ui_ready_before_guardian: bool = False,
    ) -> dict[str, object]:
        self.bootstrap_calls += 1
        result = dict(self.bootstrap_result)
        self.last_bootstrap_request = {
            "ready_timeout_seconds": ready_timeout_seconds,
            "poll_interval_seconds": poll_interval_seconds,
            "narrator_settle_seconds": narrator_settle_seconds,
            "wait_for_ui_ready_before_guardian": wait_for_ui_ready_before_guardian,
        }
        return result

    def pause_daemon(self) -> dict[str, object]:
        self.daemon_state = {"state": "paused", "pid": self.daemon_state.get("pid")}
        return dict(self.daemon_state)

    def get_knowledge_status(self) -> dict[str, object]:
        return {"ready": False, "index_path": "memory://test-index"}

    def get_settings(self) -> dict[str, object]:
        return dict(self.settings)

    def update_settings(self, patch: dict[str, object]) -> dict[str, object]:
        self.settings.update(patch)
        return dict(self.settings)

    def get_tray_state(self) -> dict[str, object]:
        return {
            "tooltip": f"WeChat AI: {self.daemon_state['state']}",
            "menu_items": [
                {"item_id": "show", "label": "显示主界面", "action": "show_window", "enabled": True},
                {"item_id": "start", "label": "开始守护", "action": "start_daemon", "enabled": self.daemon_state["state"] != "running"},
                {"item_id": "pause", "label": "暂停守护", "action": "pause_daemon", "enabled": self.daemon_state["state"] == "running"},
                {"item_id": "stop", "label": "停止守护", "action": "stop_daemon", "enabled": self.daemon_state["state"] != "stopped"},
                {"item_id": "exit", "label": "退出应用", "action": "exit_app", "enabled": True},
            ],
            "recommended_action": "pause_daemon" if self.daemon_state["state"] == "running" else "start_daemon",
        }

    def get_schedule_status(self) -> dict[str, object]:
        return {
            "enabled": bool(self.settings.get("schedule_enabled", False)),
            "should_run": True,
            "next_action": "none",
            "reason": "schedule_disabled",
        }

    def apply_schedule_tick(self) -> dict[str, object]:
        return {
            "action": "noop",
            "daemon": dict(self.daemon_state),
            "schedule": self.get_schedule_status(),
        }

    def list_customers(self) -> list[dict[str, object]]:
        return [{"customer_id": "user_001", "display_name": "张先生", "tags": ["意向客户"]}]

    def get_customer(self, customer_id: str) -> dict[str, object]:
        return {"customer_id": customer_id, "display_name": "张先生", "status": "confirmed"}

    def list_identity_drafts(self) -> list[dict[str, object]]:
        return [{"draft_user_id": "draft_001"}]

    def list_identity_candidates(self) -> list[dict[str, object]]:
        return [{"candidate_id": "candidate_001"}]

    def get_global_self_identity(self) -> dict[str, object]:
        return {"display_name": "碱水", "identity_facts": ["我是产品负责人"]}

    def update_global_self_identity(self, patch: dict[str, object]) -> dict[str, object]:
        return {"display_name": patch.get("display_name", "碱水"), "identity_facts": patch.get("identity_facts", [])}

    def build_prompt_acceptance_preview(
        self,
        user_id: str,
        *,
        latest_message: str,
        tags: list[str] | None = None,
        display_name: str = "",
        relationship_to_me: str | None = None,
        knowledge_limit: int = 3,
        scene: str = "friend",
    ) -> dict[str, object]:
        return {
            "resolved_user_id": user_id,
            "scene": scene,
            "latest_message": latest_message,
            "self_identity_profile": {
                "display_name": display_name or "碱水",
                "identity_facts": ["我是产品顾问"],
                "relationship": relationship_to_me or "",
                "tags": list(tags or []),
            },
            "knowledge_results": [
                {"chunk_id": "chunk_001", "text": "试用政策：支持 7 天体验，可先登记后开通。", "score": 0.9}
            ][:knowledge_limit],
            "prompt_preview": "## Self Identity Summary\nIdentity facts: 我是产品顾问\n\n## Retrieved Knowledge\n1. 试用政策：支持 7 天体验，可先登记后开通。",
        }

    def build_knowledge_acceptance_snapshot(self, query: str, *, imported_files: list[str] | None = None) -> dict[str, object]:
        return {
            "imported_files": list(imported_files or []),
            "search_query": query,
            "retrieved_chunk_ids": ["chunk_001"],
            "retrieved_chunks": [{"chunk_id": "chunk_001", "text": f"命中: {query}", "score": 0.9}],
            "knowledge_status": self.get_knowledge_status(),
            "web_build_status": "built",
        }

    def search_knowledge(self, query: str, *, limit: int = 3) -> list[dict[str, object]]:
        return [{"chunk_id": "chunk_001", "text": f"命中: {query}", "score": 0.9}][:limit]

    def import_knowledge_files(self, file_paths: list[str]) -> dict[str, object]:
        return {"files": [{"file_name": Path(path).name, "status": "imported"} for path in file_paths], "index_rebuilt": True}

    def build_web_knowledge_from_documents(self, file_paths: list[str], *, search_limit: int = 5) -> dict[str, object]:
        return {"documents": list(file_paths), "search_limit": search_limit, "status": "built"}

    def get_recent_logs(self, *, limit: int = 20) -> list[dict[str, object]]:
        self.recent_logs_calls += 1
        return self.log_events[-limit:]

    def get_privacy_policy(self) -> dict[str, object]:
        return dict(self.settings["privacy"])  # type: ignore[arg-type]

    def update_privacy_policy(self, patch: dict[str, object]) -> dict[str, object]:
        privacy = dict(self.settings["privacy"])  # type: ignore[arg-type]
        privacy.update(patch)
        self.settings["privacy"] = privacy
        return privacy

    def get_wechat_environment_status(self) -> dict[str, object]:
        self.environment_calls += 1
        return dict(self.environment_status)

    def get_conversation_control(self, conversation_id: str) -> dict[str, object]:
        return {
            "conversation_id": conversation_id,
            "human_takeover": conversation_id in self.settings["human_takeover_sessions"],
            "paused": conversation_id in self.settings["paused_sessions"],
            "whitelisted": conversation_id in self.settings["whitelist"],
            "blacklisted": conversation_id in self.settings["blacklist"],
        }

    def update_conversation_control(self, conversation_id: str, patch: dict[str, object]) -> dict[str, object]:
        for payload_key, settings_key in (
            ("human_takeover", "human_takeover_sessions"),
            ("paused", "paused_sessions"),
            ("whitelisted", "whitelist"),
            ("blacklisted", "blacklist"),
        ):
            values = list(self.settings[settings_key])  # type: ignore[arg-type]
            if patch.get(payload_key) is True and conversation_id not in values:
                values.append(conversation_id)
            if patch.get(payload_key) is False and conversation_id in values:
                values.remove(conversation_id)
            self.settings[settings_key] = values
        return self.get_conversation_control(conversation_id)

    def apply_retention_policy(self) -> dict[str, object]:
        return {"logs_removed": 1, "memory_files_trimmed": 0}

    def list_conversations(self) -> list[dict[str, object]]:
        return [
            {
                "conversation_id": "friend:alice",
                "title": "Alice",
                "is_group": False,
                "latest_message": "请问支持试用吗？",
                "unread_count": 1,
            }
        ]

    def get_conversation(self, conversation_id: str) -> dict[str, object]:
        return {
            "conversation": {
                "conversation_id": conversation_id,
                "title": "Alice",
                "is_group": False,
                "latest_message": "请问支持试用吗？",
                "unread_count": 1,
            },
            "messages": [
                {
                    "message_id": "msg_001",
                    "conversation_id": conversation_id,
                    "sender": "Alice",
                    "text": "请问支持试用吗？",
                    "direction": "incoming",
                }
            ],
            "control": self.get_conversation_control(conversation_id),
        }

    def suggest_reply(self, conversation_id: str, message_text: str):
        return {
            "conversation_id": conversation_id,
            "input_text": message_text,
            "suggestion": "支持 7 天试用。",
            "status": "ready",
        }

    def send_reply(self, conversation_id: str, text: str):
        if not text.strip():
            return {
                "status": "blocked",
                "allowed": False,
                "conversation_id": conversation_id,
                "text": text,
                "reason_code": "EMPTY_TEXT",
                "reason": "Reply text is empty",
            }
        return {
            "status": "not_implemented",
            "allowed": True,
            "conversation_id": conversation_id,
            "text": text,
            "reason_code": "",
            "reason": "",
        }


def test_ping_returns_versioned_success_shape() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/ping", headers={"x-trace-id": "trace-test"})
    payload = response.json()

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-test"
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["trace_id"] == "trace-test"
    assert payload["data"]["pong"] is True


def test_health_wraps_desktop_service_status() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["runtime"]["daemon_state"] == "stopped"
    assert payload["data"]["knowledge"]["ready"] is False
    assert payload["trace_id"]


def test_openapi_schema_is_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/openapi.json")
    payload = response.json()

    assert response.status_code == 200
    assert payload["info"]["title"] == "WeChat AI Local API"
    assert "/api/v1/ping" in payload["paths"]
    assert "/api/v1/health" in payload["paths"]
    assert "/api/v1/runtime/status" in payload["paths"]
    assert "/api/v1/runtime/start" in payload["paths"]
    assert "/api/v1/runtime/bootstrap-check" in payload["paths"]
    assert "/api/v1/runtime/bootstrap-start" in payload["paths"]
    assert "/api/v1/runtime/stop" in payload["paths"]
    assert "/api/v1/runtime/restart" in payload["paths"]
    assert "/api/v1/runtime/pause" in payload["paths"]
    assert "/api/v1/dashboard/summary" in payload["paths"]
    assert "/api/v1/debug/prompt-preview" in payload["paths"]
    assert "/api/v1/debug/knowledge-acceptance" in payload["paths"]
    assert "/api/v1/shell/tray-state" in payload["paths"]
    assert "/api/v1/shell/schedule-status" in payload["paths"]
    assert "/api/v1/shell/schedule/tick" in payload["paths"]
    assert "/api/v1/settings" in payload["paths"]
    assert "/api/v1/customers" in payload["paths"]
    assert "/api/v1/conversations" in payload["paths"]
    assert "/api/v1/conversations/{conversation_id}" in payload["paths"]
    assert "/api/v1/conversations/{conversation_id}/suggest" in payload["paths"]
    assert "/api/v1/conversations/{conversation_id}/send" in payload["paths"]
    assert "/api/v1/knowledge/status" in payload["paths"]
    assert "/api/v1/logs/recent" in payload["paths"]
    assert "/api/v1/privacy/policy" in payload["paths"]
    assert "/api/v1/privacy/apply-retention" in payload["paths"]
    assert "/api/v1/controls/conversations/{conversation_id}" in payload["paths"]
    assert "/api/v1/environment/wechat" in payload["paths"]
    assert "/api/v1/events" in payload["paths"]
    assert "ApiResponse" in str(payload["components"]["schemas"])


def test_sse_events_endpoint_replays_recent_event_and_closes_in_once_mode() -> None:
    from wechat_ai.server import create_app

    app = create_app(desktop_service=FakeDesktopService())
    event = app.state.event_bus.publish(
        "runtime.status",
        {"state": "running", "mode": "global"},
        trace_id="trace-event",
    )
    client = TestClient(app)

    response = client.get("/api/v1/events?replay=10&once=true")
    body = response.text

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert f"id: {event['id']}" in body
    assert "event: runtime.status" in body
    assert '"state":"running"' in body
    assert '"mode":"global"' in body
    assert '"trace_id":"trace-event"' in body


def test_event_bus_subscription_replays_and_receives_future_events_without_gap() -> None:
    from wechat_ai.server.services.events import EventBus

    async def scenario() -> None:
        bus = EventBus()
        first = bus.publish("runtime.status", {"state": "running"}, trace_id="trace-first")
        replay_events, subscription = bus.subscribe(replay=1)
        try:
            second = bus.publish("message.received", {"conversation_id": "friend:alice"}, trace_id="trace-second")
            streamed = await bus.next_event(subscription, timeout=0.2)
        finally:
            bus.unsubscribe(subscription)

        assert [event["id"] for event in replay_events] == [first["id"]]
        assert streamed is not None
        assert streamed["id"] == second["id"]
        assert streamed["trace_id"] == "trace-second"

    asyncio.run(scenario())


def test_runtime_actions_publish_runtime_status_events() -> None:
    from wechat_ai.server import create_app

    app = create_app(desktop_service=FakeDesktopService())
    client = TestClient(app)

    client.post("/api/v1/runtime/start", json={"mode": "global"}, headers={"x-trace-id": "trace-start"})
    response = client.get("/api/v1/events?replay=10&once=true")

    assert "event: runtime.status" in response.text
    assert '"state":"running"' in response.text
    assert '"trace_id":"trace-start"' in response.text


def test_runtime_bootstrap_start_endpoint_runs_bootstrap_before_starting_daemon() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    response = client.post("/api/v1/runtime/bootstrap-start", json={"mode": "global"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["state"] == "running"
    assert payload["data"]["bootstrap"]["ok"] is True
    assert service.last_bootstrap_request["wait_for_ui_ready_before_guardian"] is True
    assert payload["data"]["bootstrap"]["status_lines"][-1].startswith("检测到微信已运行")
    assert service.bootstrap_calls == 1
    assert service.started == 1


def test_runtime_bootstrap_check_only_preflights_without_starting_daemon() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    response = client.post("/api/v1/runtime/bootstrap-check", json={"mode": "global"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["state"] == "stopped"
    assert payload["data"]["running"] is False
    assert payload["data"]["bootstrap"]["ok"] is True
    assert payload["data"]["bootstrap"]["guardian_started"] is False
    assert service.last_bootstrap_request["wait_for_ui_ready_before_guardian"] is True
    assert service.bootstrap_calls == 1
    assert service.started == 0


def test_runtime_bootstrap_start_returns_wechat_window_error_when_preflight_fails() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    service.bootstrap_result = {
        "ok": False,
        "wechat_started": True,
        "narrator_started": True,
        "ui_ready": False,
        "guardian_started": False,
        "narrator_stopped": False,
        "attempts": 20,
        "message": "在设定时间内未识别到微信主界面，请确认已扫码登录且讲述人已正常工作。",
        "guardian_command": [],
        "guardian_exit_code": None,
        "status_lines": ["等待微信主界面可识别，第 20 次检测...", "等待超时，未识别到微信主界面。"],
        "environment": {"wechat_running": True, "narrator_required": True, "ui_ready": False},
    }
    client = TestClient(create_app(desktop_service=service))

    response = client.post("/api/v1/runtime/bootstrap-start", json={"mode": "global"})
    payload = response.json()

    assert response.status_code == 409
    assert payload["success"] is False
    assert payload["error"]["code"] == "WECHAT_WINDOW_NOT_FOUND"
    assert payload["error"]["detail"]["status_lines"][-1].startswith("等待超时")
    assert service.bootstrap_calls == 1
    assert service.started == 0


def test_runtime_pause_returns_paused_state() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    client.post("/api/v1/runtime/start", json={"mode": "global"})
    paused = client.post("/api/v1/runtime/pause", headers={"x-trace-id": "trace-pause"})
    payload = paused.json()

    assert paused.status_code == 200
    assert payload["success"] is True
    assert payload["trace_id"] == "trace-pause"
    assert payload["data"]["state"] == "paused"
    assert payload["data"]["running"] is False


def test_shell_tray_state_endpoint_is_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/shell/tray-state")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert "tooltip" in payload["data"]
    assert "menu_items" in payload["data"]


def test_shell_schedule_endpoints_are_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    status = client.get("/api/v1/shell/schedule-status")
    tick = client.post("/api/v1/shell/schedule/tick")

    assert status.status_code == 200
    assert status.json()["success"] is True
    assert "enabled" in status.json()["data"]
    assert tick.status_code == 200
    assert tick.json()["success"] is True
    assert "action" in tick.json()["data"]


def test_debug_prompt_preview_endpoint_is_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get(
        "/api/v1/debug/prompt-preview",
        params={
            "user_id": "user_001",
            "latest_message": "你们支持试用吗？",
            "relationship_to_me": "customer",
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["resolved_user_id"] == "user_001"
    assert "我是产品顾问" in payload["data"]["prompt_preview"]


def test_debug_knowledge_acceptance_endpoint_is_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get(
        "/api/v1/debug/knowledge-acceptance",
        params={"q": "试用政策", "imported_files": ["policy.txt"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["imported_files"] == ["policy.txt"]
    assert payload["data"]["search_query"] == "试用政策"
    assert payload["data"]["retrieved_chunk_ids"] == ["chunk_001"]


def test_background_event_relay_primes_bus_without_per_client_sync_calls() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    service.log_events = [
        {
            "timestamp": "2026-04-24T10:10:00Z",
            "event_type": "message_received",
            "conversation_id": "friend:alice",
            "sender": "Alice",
            "text": "hello",
            "is_group": False,
            "trace_id": "trace-msg",
        }
    ]
    app = create_app(desktop_service=service, event_relay_interval_seconds=60.0)

    with TestClient(app) as client:
        startup_log_calls = service.recent_logs_calls
        startup_environment_calls = service.environment_calls
        primed_events = app.state.event_bus.recent(10)

        client.get("/api/v1/events?once=true")
        client.get("/api/v1/events?once=true")

        assert any(event["type"] == "message.received" for event in primed_events)
        assert service.recent_logs_calls == startup_log_calls
        assert service.environment_calls == startup_environment_calls
        assert service.environment_calls == 0


def test_runtime_event_relay_bridges_runtime_logs_and_environment_changes() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    service.log_events = [
        {
            "timestamp": "2026-04-24T10:10:00Z",
            "event_type": "message_received",
            "conversation_id": "friend:alice",
            "sender": "Alice",
            "text": "hello",
            "is_group": False,
            "trace_id": "trace-msg",
        },
        {
            "timestamp": "2026-04-24T10:11:00Z",
            "event_type": "reply.error",
            "trace_id": "trace-err",
            "message": "send failed",
            "exception_type": "RuntimeError",
        },
    ]
    app = create_app(desktop_service=service)

    app.state.event_relay.sync(service, app.state.event_bus, trace_id="trace-sync-1", include_environment=True)
    service.environment_status = {
        "wechat_running": True,
        "narrator_required": False,
        "ui_ready": False,
        "ui_probe": {
            "window_ready": True,
            "window_minimized": True,
            "input_ready": False,
            "current_chat": "",
        },
    }
    app.state.event_relay.sync(service, app.state.event_bus, trace_id="trace-sync-2", include_environment=True)

    events = app.state.event_bus.recent(10)
    event_types = [event["type"] for event in events]

    assert "message.received" in event_types
    assert "log.event" in event_types
    assert "error" in event_types
    received = next(event for event in events if event["type"] == "message.received")
    assert received["data"]["conversation_id"] == "friend:alice"
    assert received["data"]["text"] == "hello"
    environment_log = next(
        event
        for event in events
        if event["type"] == "log.event" and event["data"].get("event_type") == "window.environment.changed"
    )
    assert environment_log["data"]["snapshot"]["ui_ready"] is False
    assert environment_log["data"]["snapshot"]["ui_probe"]["window_minimized"] is True


def test_frontend_actions_publish_message_control_and_knowledge_events() -> None:
    from wechat_ai.server import create_app

    app = create_app(desktop_service=FakeDesktopService())
    client = TestClient(app)

    client.post(
        "/api/v1/conversations/friend%3Aalice/send",
        json={"text": "hello"},
        headers={"x-trace-id": "trace-send"},
    )
    client.patch(
        "/api/v1/controls/conversations/friend%3Aalice",
        json={"paused": True},
        headers={"x-trace-id": "trace-control"},
    )
    client.post(
        "/api/v1/knowledge/import",
        json={"file_paths": ["C:/tmp/faq.pdf"]},
        headers={"x-trace-id": "trace-knowledge"},
    )

    body = client.get("/api/v1/events?replay=20&once=true").text

    assert "event: message.sent" in body
    assert "event: log.event" in body
    assert "event: knowledge.progress" in body
    assert '"conversation_id":"friend:alice"' in body
    assert '"trace_id":"trace-send"' in body
    assert '"trace_id":"trace-control"' in body
    assert '"trace_id":"trace-knowledge"' in body


def test_runtime_status_start_stop_flow() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    initial = client.get("/api/v1/runtime/status").json()
    assert initial["success"] is True
    assert initial["data"]["state"] == "stopped"
    assert initial["data"]["running"] is False

    started = client.post("/api/v1/runtime/start", json={"mode": "global"}).json()
    assert started["success"] is True
    assert started["data"]["state"] == "running"
    assert started["data"]["running"] is True
    assert service.started == 1

    running = client.get("/api/v1/runtime/status").json()
    assert running["data"]["state"] == "running"
    assert running["data"]["running"] is True

    stopped = client.post("/api/v1/runtime/stop").json()
    assert stopped["success"] is True
    assert stopped["data"]["state"] == "stopped"
    assert stopped["data"]["running"] is False
    assert service.stopped == 1


def test_runtime_restart_stops_existing_runtime_and_starts_again() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    client.post("/api/v1/runtime/start", json={"mode": "global"})
    restarted = client.post("/api/v1/runtime/restart", json={"mode": "global"}).json()

    assert restarted["success"] is True
    assert restarted["data"]["state"] == "running"
    assert restarted["data"]["running"] is True
    assert service.stopped == 1
    assert service.started == 2


def test_runtime_start_rejects_duplicate_start() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    first = client.post("/api/v1/runtime/start", json={"mode": "global"})
    second = client.post("/api/v1/runtime/start", json={"mode": "global"}, headers={"x-trace-id": "trace-runtime"})
    payload = second.json()

    assert first.status_code == 200
    assert second.status_code == 409
    assert payload["success"] is False
    assert payload["trace_id"] == "trace-runtime"
    assert payload["error"]["code"] == "RUNTIME_ALREADY_RUNNING"
    assert service.started == 1


def test_runtime_stop_rejects_when_not_running() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))
    response = client.post("/api/v1/runtime/stop", headers={"x-trace-id": "trace-stop"})
    payload = response.json()

    assert response.status_code == 409
    assert payload["success"] is False
    assert payload["trace_id"] == "trace-stop"
    assert payload["error"]["code"] == "RUNTIME_NOT_RUNNING"
    assert service.stopped == 0


def test_runtime_start_rejects_unsupported_mode() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))
    response = client.post("/api/v1/runtime/start", json={"mode": "friend"})
    payload = response.json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"]["code"] == "CONFIG_INVALID"
    assert payload["error"]["detail"]["supported_modes"] == ["global"]
    assert service.started == 0


def test_api_errors_use_stable_error_shape() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/debug/error?kind=config", headers={"x-trace-id": "trace-api"})
    payload = response.json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["trace_id"] == "trace-api"
    assert payload["error"]["code"] == "CONFIG_INVALID"
    assert payload["error"]["message"] == "Debug API error"
    assert payload["error"]["detail"]["kind"] == "config"


def test_error_catalog_distinguishes_http_errors_from_business_statuses() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/errors/catalog")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["error"] is None
    http_codes = {item["code"] for item in payload["data"]["http_errors"]}
    send_statuses = {item["status"] for item in payload["data"]["send_reply_statuses"]}
    send_reason_codes = {item["code"] for item in payload["data"]["send_reply_reason_codes"]}
    assert {"REQUEST_INVALID", "RUNTIME_ALREADY_RUNNING", "RUNTIME_NOT_RUNNING", "UNKNOWN_ERROR"} <= http_codes
    assert {"blocked", "not_implemented", "sent", "unconfirmed", "failed"} <= send_statuses
    assert {"EMPTY_TEXT", "HUMAN_TAKEOVER", "CONVERSATION_PAUSED", "BLACKLISTED"} <= send_reason_codes


def test_validation_errors_use_stable_error_shape() -> None:
    from fastapi import APIRouter, Query

    from wechat_ai.server import create_app

    app = create_app(desktop_service=FakeDesktopService())
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(value: int = Query(...)) -> dict[str, int]:
        return {"value": value}

    app.include_router(router, prefix="/api/v1")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/needs-int?value=nope", headers={"x-trace-id": "trace-validation"})
    payload = response.json()

    assert response.status_code == 422
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["trace_id"] == "trace-validation"
    assert payload["error"]["code"] == "REQUEST_INVALID"
    assert payload["error"]["message"] == "Invalid request"
    assert isinstance(payload["error"]["detail"], list)


def test_frontend_mutation_requests_reject_unknown_fields() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    responses = [
        client.post("/api/v1/runtime/start", json={"mode": "global", "unexpected": True}),
        client.patch("/api/v1/settings", json={"unexpected": True}),
        client.patch("/api/v1/privacy/policy", json={"unexpected": True}),
        client.patch("/api/v1/controls/conversations/user_001", json={"unexpected": True}),
        client.patch("/api/v1/identity/self/global", json={"unexpected": True}),
    ]

    for response in responses:
        payload = response.json()
        assert response.status_code == 422
        assert payload["success"] is False
        assert payload["error"]["code"] == "REQUEST_INVALID"


def test_knowledge_mutation_requests_enforce_safe_boundaries() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    empty_import = client.post("/api/v1/knowledge/import", json={"file_paths": []})
    empty_web_build = client.post("/api/v1/knowledge/web-build", json={"file_paths": [], "search_limit": 2})
    excessive_web_limit = client.post(
        "/api/v1/knowledge/web-build",
        json={"file_paths": ["C:/tmp/faq.pdf"], "search_limit": 99},
    )
    invalid_search_limit = client.get("/api/v1/knowledge/search?q=faq&limit=99")

    for response in (empty_import, empty_web_build, excessive_web_limit, invalid_search_limit):
        payload = response.json()
        assert response.status_code == 422
        assert payload["success"] is False
        assert payload["error"]["code"] == "REQUEST_INVALID"


def test_unexpected_errors_use_stable_error_shape() -> None:
    from fastapi import APIRouter

    from wechat_ai.server import create_app

    app = create_app(desktop_service=FakeDesktopService())
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail")

    app.include_router(router, prefix="/api/v1")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/boom", headers={"x-trace-id": "trace-error"})
    payload = response.json()

    assert response.status_code == 500
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["trace_id"] == "trace-error"
    assert payload["error"]["code"] == "UNKNOWN_ERROR"
    assert payload["error"]["message"] == "Internal server error"
    assert "secret detail" not in str(payload)


def test_frontend_dashboard_and_settings_endpoints_are_available() -> None:
    from wechat_ai.server import create_app

    service = FakeDesktopService()
    client = TestClient(create_app(desktop_service=service))

    dashboard = client.get("/api/v1/dashboard/summary").json()
    settings = client.get("/api/v1/settings").json()
    updated = client.patch("/api/v1/settings", json={"auto_reply_enabled": False}).json()

    assert dashboard["success"] is True
    assert dashboard["data"]["app"]["daemon_state"] == "stopped"
    assert dashboard["data"]["runtime"]["state"] == "stopped"
    assert settings["data"]["auto_reply_enabled"] is True
    assert updated["data"]["auto_reply_enabled"] is False


def test_frontend_customer_identity_and_knowledge_endpoints_are_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    customers = client.get("/api/v1/customers").json()
    customer = client.get("/api/v1/customers/user_001").json()
    identity = client.get("/api/v1/identity/self/global").json()
    identity_updated = client.patch("/api/v1/identity/self/global", json={"display_name": "新版身份"}).json()
    knowledge = client.get("/api/v1/knowledge/status").json()
    search = client.get("/api/v1/knowledge/search?q=试用&limit=1").json()
    imported = client.post("/api/v1/knowledge/import", json={"file_paths": ["C:/tmp/faq.pdf"]}).json()
    web_build = client.post("/api/v1/knowledge/web-build", json={"file_paths": ["C:/tmp/faq.pdf"], "search_limit": 2}).json()

    assert customers["data"][0]["display_name"] == "张先生"
    assert customer["data"]["customer_id"] == "user_001"
    assert identity["data"]["display_name"] == "碱水"
    assert identity_updated["data"]["display_name"] == "新版身份"
    assert knowledge["data"]["ready"] is False
    assert search["data"][0]["chunk_id"] == "chunk_001"
    assert imported["data"]["index_rebuilt"] is True
    assert web_build["data"]["status"] == "built"


def test_message_page_conversation_and_suggestion_endpoints_are_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    conversations = client.get("/api/v1/conversations").json()
    detail = client.get("/api/v1/conversations/friend%3Aalice").json()
    suggestion = client.post(
        "/api/v1/conversations/friend%3Aalice/suggest",
        json={"message_text": "请问支持试用吗？"},
    ).json()
    blocked = client.post(
        "/api/v1/conversations/friend%3Aalice/send",
        json={"text": "   "},
    ).json()
    allowed = client.post(
        "/api/v1/conversations/friend%3Aalice/send",
        json={"text": "您好，支持 7 天试用。"},
    ).json()

    assert conversations["success"] is True
    assert conversations["data"][0]["conversation_id"] == "friend:alice"
    assert detail["data"]["conversation"]["title"] == "Alice"
    assert detail["data"]["messages"][0]["direction"] == "incoming"
    assert detail["data"]["control"]["paused"] is False
    assert suggestion["data"]["status"] == "ready"
    assert suggestion["data"]["suggestion"] == "支持 7 天试用。"
    assert blocked["data"]["status"] == "blocked"
    assert blocked["data"]["reason_code"] == "EMPTY_TEXT"
    assert blocked["success"] is True
    assert blocked["error"] is None
    assert allowed["data"]["allowed"] is True
    assert allowed["data"]["status"] == "not_implemented"


def test_frontend_ops_privacy_and_environment_endpoints_are_available() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    logs = client.get("/api/v1/logs/recent?limit=5").json()
    privacy = client.get("/api/v1/privacy/policy").json()
    updated = client.patch("/api/v1/privacy/policy", json={"log_retention_days": 7}).json()
    environment = client.get("/api/v1/environment/wechat").json()
    control = client.patch(
        "/api/v1/controls/conversations/user_001",
        json={"human_takeover": True, "paused": True, "blacklisted": True},
    ).json()
    cleanup = client.post("/api/v1/privacy/apply-retention").json()

    assert logs["data"][0]["event_type"] == "heartbeat"
    assert "token=[redacted]" in logs["data"][0]["message"]
    assert privacy["data"]["redact_sensitive_logs"] is True
    assert updated["data"]["log_retention_days"] == 7
    assert environment["data"]["wechat_running"] is True
    assert control["data"]["human_takeover"] is True
    assert control["data"]["paused"] is True
    assert control["data"]["blacklisted"] is True
    assert cleanup["data"]["logs_removed"] == 1


def test_recent_logs_can_filter_by_event_type_trace_id_and_errors() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))

    generated = client.get("/api/v1/logs/recent?event_type=reply.generated").json()
    traced = client.get("/api/v1/logs/recent?trace_id=trace-blocked").json()
    errors = client.get("/api/v1/logs/recent?only_errors=true").json()

    assert generated["success"] is True
    assert [event["event_type"] for event in generated["data"]] == ["reply.generated"]
    assert [event["trace_id"] for event in traced["data"]] == ["trace-blocked"]
    assert [event["event_type"] for event in errors["data"]] == ["reply.error", "send.blocked"]


def test_logs_summary_reports_recent_error_count_and_last_event_time() -> None:
    from wechat_ai.server import create_app

    client = TestClient(create_app(desktop_service=FakeDesktopService()))
    response = client.get("/api/v1/logs/summary?limit=3")
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"] == {
        "recent_count": 3,
        "recent_error_count": 2,
        "last_event_time": "2026-04-24T10:03:00Z",
    }


def main() -> None:
    test_ping_returns_versioned_success_shape()
    test_health_wraps_desktop_service_status()
    test_openapi_schema_is_available()
    test_sse_events_endpoint_replays_recent_event_and_closes_in_once_mode()
    test_event_bus_subscription_replays_and_receives_future_events_without_gap()
    test_runtime_actions_publish_runtime_status_events()
    test_runtime_bootstrap_start_endpoint_runs_bootstrap_before_starting_daemon()
    test_runtime_bootstrap_check_only_preflights_without_starting_daemon()
    test_runtime_bootstrap_start_returns_wechat_window_error_when_preflight_fails()
    test_runtime_pause_returns_paused_state()
    test_shell_tray_state_endpoint_is_available()
    test_shell_schedule_endpoints_are_available()
    test_debug_prompt_preview_endpoint_is_available()
    test_debug_knowledge_acceptance_endpoint_is_available()
    test_background_event_relay_primes_bus_without_per_client_sync_calls()
    test_runtime_event_relay_bridges_runtime_logs_and_environment_changes()
    test_frontend_actions_publish_message_control_and_knowledge_events()
    test_runtime_status_start_stop_flow()
    test_runtime_restart_stops_existing_runtime_and_starts_again()
    test_runtime_start_rejects_duplicate_start()
    test_runtime_stop_rejects_when_not_running()
    test_runtime_start_rejects_unsupported_mode()
    test_api_errors_use_stable_error_shape()
    test_error_catalog_distinguishes_http_errors_from_business_statuses()
    test_validation_errors_use_stable_error_shape()
    test_frontend_mutation_requests_reject_unknown_fields()
    test_knowledge_mutation_requests_enforce_safe_boundaries()
    test_unexpected_errors_use_stable_error_shape()
    test_frontend_dashboard_and_settings_endpoints_are_available()
    test_frontend_customer_identity_and_knowledge_endpoints_are_available()
    test_message_page_conversation_and_suggestion_endpoints_are_available()
    test_frontend_ops_privacy_and_environment_endpoints_are_available()
    test_recent_logs_can_filter_by_event_type_trace_id_and_errors()
    test_logs_summary_reports_recent_error_count_and_last_event_time()
    print("wechat_ai server unit tests passed")


if __name__ == "__main__":
    main()
