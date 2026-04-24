from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Mapping, Sequence

from wechat_ai import paths
from wechat_ai.identity import identity_admin
from wechat_ai.logging_utils import sanitize_text, tail_jsonl_events, utc_timestamp
from wechat_ai.models import Message
from wechat_ai.rag.embeddings import FakeEmbeddings
from wechat_ai.rag.retriever import LocalIndexRetriever
from wechat_ai.rag.web_knowledge_builder import WebKnowledgeBuilder
from wechat_ai.self_identity import admin as self_identity_admin

from .daemon_controller import DaemonController
from .knowledge_importer import KnowledgeImporter
from .models import AppStatus, ConversationListItem, CustomerRecord, ReplySuggestion
from .schedule_manager import ScheduleManager
from .settings_store import DesktopSettingsStore
from .tray_adapter import TrayAdapter
from .wechat_bootstrap import is_process_running, locate_existing_wechat_path
from .wechat_window_probe import PyWeixinVisualSendConfirmer, WeChatWindowProbe


class _NoOpDaemonRunner:
    def __init__(self) -> None:
        self._running: set[int] = set()
        self._next_pid = 1001

    def launch(
        self,
        *,
        run_silently: bool = True,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 60.0,
        error_backoff_seconds: float = 5.0,
        stop_event: threading.Event | None = None,
    ) -> int:
        del run_silently, poll_interval, heartbeat_interval, error_backoff_seconds, stop_event
        pid = self._next_pid
        self._next_pid += 1
        self._running.add(pid)
        return pid

    def stop(self, pid: int) -> bool:
        self._running.discard(pid)
        return True

    def is_running(self, pid: int | None) -> bool:
        return pid is not None and pid in self._running


class PyWeixinReplySender:
    def send_reply(self, *, conversation_id: str, text: str, is_group: bool = False) -> dict[str, object]:
        del is_group
        from pyweixin import Messages

        target = _conversation_title(conversation_id)
        Messages.send_messages_to_friend(friend=target, messages=[text], close_weixin=False)
        return {"sent": True, "target": target}


class DesktopAppService:
    def __init__(
        self,
        *,
        data_root: Path | None = None,
        settings_store: DesktopSettingsStore | None = None,
        knowledge_importer: KnowledgeImporter | None = None,
        identity_admin_module: Any | None = None,
        daemon_runner: Any | None = None,
        web_knowledge_builder: Any | None = None,
        reply_pipeline: Any | None = None,
        reply_sender: Any | None = None,
        send_confirmer: Any | None = None,
        wechat_window_probe: Any | None = None,
    ) -> None:
        root = Path(data_root) if data_root is not None else paths.DATA_DIR
        self.data_root = root
        self.app_dir = root / "app"
        self.identity_dir = root / "identity"
        self.self_identity_dir = root / "self_identity"
        self.runtime_log_path = root / "logs" / "runtime_events.jsonl"
        self.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.conversation_store_path = self.app_dir / "conversations.json"
        self.settings_store = settings_store or DesktopSettingsStore(self.app_dir / "desktop_settings.json")
        self.daemon_controller = DaemonController(self.app_dir / "daemon_state.json")
        self.daemon_runner = daemon_runner or _NoOpDaemonRunner()
        self.schedule_manager = ScheduleManager()
        self.tray_adapter = TrayAdapter()
        self._daemon_stop_event: threading.Event | None = None
        self.knowledge_importer = knowledge_importer or KnowledgeImporter(
            knowledge_dir=root / "knowledge",
            uploads_dir=root / "knowledge" / "uploads",
            index_path=root / "knowledge" / "local_knowledge_index.json",
        )
        self.web_knowledge_builder = web_knowledge_builder or WebKnowledgeBuilder(
            knowledge_dir=root / "knowledge",
            knowledge_importer=self.knowledge_importer,
        )
        self.reply_pipeline = reply_pipeline
        self.reply_sender = reply_sender
        self.send_confirmer = send_confirmer
        self.wechat_window_probe = wechat_window_probe
        self.identity_admin = identity_admin_module or identity_admin
        self.self_identity_admin = self_identity_admin

    def get_app_status(self) -> AppStatus:
        settings = self.get_settings()
        daemon_status = self._normalized_daemon_status()
        pending_count = len(self.list_identity_candidates()) + len(self.list_identity_drafts())
        knowledge_status = self.get_knowledge_status()
        return AppStatus(
            wechat_status="unknown",
            daemon_state=daemon_status["state"],
            auto_reply_enabled=settings.auto_reply_enabled,
            today_received=int(daemon_status["today_received"]),
            today_replied=int(daemon_status["today_replied"]),
            pending_count=pending_count,
            knowledge_index_ready=bool(knowledge_status["ready"]),
            last_heartbeat=daemon_status.get("last_heartbeat"),
        )

    def get_settings(self):
        return self.settings_store.load()

    def update_settings(self, patch: Mapping[str, object]):
        return self.settings_store.update(patch)

    def get_daemon_status(self) -> dict[str, object]:
        return self._normalized_daemon_status()

    def start_daemon(self) -> dict[str, object]:
        settings = self.get_settings()
        stop_event = threading.Event()
        self._daemon_stop_event = stop_event
        pid = self.daemon_runner.launch(
            run_silently=settings.run_silently,
            poll_interval=1.0,
            heartbeat_interval=60.0,
            error_backoff_seconds=5.0,
            stop_event=stop_event,
        )
        status = self.daemon_controller.start(run_silently=settings.run_silently, pid=pid)
        return asdict(status)

    def pause_daemon(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if self._daemon_stop_event is not None:
            self._daemon_stop_event.set()
        if status.pid is not None:
            self.daemon_runner.stop(status.pid)
        updated = self.daemon_controller.pause()
        updated.pid = status.pid
        self.daemon_controller._save(updated)
        return asdict(updated)

    def stop_daemon(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if self._daemon_stop_event is not None:
            self._daemon_stop_event.set()
        if status.pid is not None:
            self.daemon_runner.stop(status.pid)
        updated = self.daemon_controller.stop()
        self._daemon_stop_event = None
        return asdict(updated)

    def apply_schedule_tick(self, *, now: datetime | None = None) -> dict[str, object]:
        schedule_status = self.schedule_manager.evaluate(self.get_settings(), now=now)
        daemon_status = self.get_daemon_status()
        if schedule_status.should_run and daemon_status["state"] != "running":
            started = self.start_daemon()
            return {"action": "start", "daemon": started, "schedule": asdict(schedule_status)}
        if not schedule_status.should_run and daemon_status["state"] == "running":
            paused = self.pause_daemon()
            return {"action": "pause", "daemon": paused, "schedule": asdict(schedule_status)}
        return {"action": "noop", "daemon": daemon_status, "schedule": asdict(schedule_status)}

    def get_tray_state(self, *, now: datetime | None = None) -> dict[str, object]:
        daemon_status = self.daemon_controller.load_status()
        schedule_status = self.schedule_manager.evaluate(self.get_settings(), now=now)
        return asdict(self.tray_adapter.build_state(daemon_status=daemon_status, schedule_status=schedule_status))

    def list_identity_drafts(self) -> list[dict[str, Any]]:
        return self.identity_admin.list_drafts(base_dir=self.identity_dir)

    def list_identity_candidates(self) -> list[dict[str, Any]]:
        return self.identity_admin.list_candidates(base_dir=self.identity_dir)

    def list_customers(self) -> list[CustomerRecord]:
        records: list[CustomerRecord] = []
        for user in self.identity_admin.list_users(base_dir=self.identity_dir):
            records.append(
                CustomerRecord(
                    customer_id=str(user["user_id"]),
                    display_name=str(user.get("canonical_name", "")),
                    status=str(user.get("status", "confirmed")),
                    tags=list(user.get("tags", [])) if isinstance(user.get("tags"), list) else [],
                    remark=str(user.get("remark", "")),
                    last_contact_at=str(user.get("updated_at", "")) or None,
                )
            )
        return records

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        for customer in self.list_customers():
            if customer.customer_id == customer_id:
                return asdict(customer) | {"display_name": customer.display_name}
        return {"status": "not_found", "customer_id": customer_id}

    def get_global_self_identity(self) -> dict[str, Any]:
        return self.self_identity_admin.load_global_profile(base_dir=self.self_identity_dir)

    def update_global_self_identity(self, patch: Mapping[str, object]) -> dict[str, Any]:
        return self.self_identity_admin.update_global_profile(patch, base_dir=self.self_identity_dir)

    def list_relationship_self_identity_profiles(self) -> list[dict[str, Any]]:
        return self.self_identity_admin.list_relationship_profiles(base_dir=self.self_identity_dir)

    def get_relationship_self_identity_profile(self, relationship: str) -> dict[str, Any]:
        return self.self_identity_admin.load_relationship_profile(relationship, base_dir=self.self_identity_dir)

    def update_relationship_self_identity_profile(
        self,
        relationship: str,
        patch: Mapping[str, object],
    ) -> dict[str, Any]:
        return self.self_identity_admin.update_relationship_profile(
            relationship,
            patch,
            base_dir=self.self_identity_dir,
        )

    def list_user_self_identity_overrides(self) -> list[dict[str, Any]]:
        return self.self_identity_admin.list_user_overrides(base_dir=self.self_identity_dir)

    def get_user_self_identity_override(self, user_id: str) -> dict[str, Any]:
        return self.self_identity_admin.load_user_override(user_id, base_dir=self.self_identity_dir)

    def update_user_self_identity_override(self, user_id: str, patch: Mapping[str, object]) -> dict[str, Any]:
        return self.self_identity_admin.update_user_override(user_id, patch, base_dir=self.self_identity_dir)

    def preview_self_identity(
        self,
        user_id: str,
        *,
        tags: Sequence[str] | None = None,
        display_name: str = "",
        relationship_to_me: str | None = None,
    ) -> dict[str, Any]:
        return self.self_identity_admin.preview_resolved_profile(
            user_id,
            tags=list(tags or []),
            display_name=display_name,
            relationship_to_me=relationship_to_me,
            base_dir=self.self_identity_dir,
        )

    def send_reply(self, conversation_id: str, text: str) -> dict[str, str]:
        preflight = self.validate_send_reply(conversation_id, text)
        if not preflight["allowed"]:
            return {
                "status": "blocked",
                "action": "send_reply",
                "allowed": False,
                "conversation_id": conversation_id,
                "text": text,
                "reason_code": str(preflight["reason_code"]),
                "reason": str(preflight["reason"]),
            }
        cleaned_text = str(text).strip()
        sender = self.reply_sender
        if sender is None and self.get_settings().real_send_enabled:
            sender = PyWeixinReplySender()
        send_confirmer = self.send_confirmer
        if send_confirmer is None and sender is not None and self.get_settings().real_send_enabled:
            send_confirmer = PyWeixinVisualSendConfirmer(probe=self._get_wechat_window_probe())
        if sender is not None:
            normalized_id = str(conversation_id).strip()
            is_group = _conversation_chat_type(conversation_id) == "group"
            try:
                send_result = sender.send_reply(
                    conversation_id=normalized_id,
                    text=cleaned_text,
                    is_group=is_group,
                )
            except Exception as exc:
                return {
                    "status": "failed",
                    "action": "send_reply",
                    "allowed": True,
                    "sent": False,
                    "conversation_id": conversation_id,
                    "text": cleaned_text,
                    "reason_code": "SEND_FAILED",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            normalized_send_result = send_result if isinstance(send_result, dict) else {}
            if send_confirmer is not None:
                try:
                    confirmation = send_confirmer.confirm_sent(
                        conversation_id=normalized_id,
                        text=cleaned_text,
                        is_group=is_group,
                        send_result=normalized_send_result,
                    )
                except Exception as exc:
                    return {
                        "status": "unconfirmed",
                        "action": "send_reply",
                        "allowed": True,
                        "sent": True,
                        "confirmed": False,
                        "conversation_id": conversation_id,
                        "text": cleaned_text,
                        "reason_code": "SEND_NOT_CONFIRMED",
                        "reason": f"{type(exc).__name__}: {exc}",
                        "send_result": normalized_send_result,
                    }
                if not _confirmation_succeeded(confirmation):
                    return {
                        "status": "unconfirmed",
                        "action": "send_reply",
                        "allowed": True,
                        "sent": True,
                        "confirmed": False,
                        "conversation_id": conversation_id,
                        "text": cleaned_text,
                        "reason_code": "SEND_NOT_CONFIRMED",
                        "reason": "",
                        "send_result": normalized_send_result,
                    }
            self.record_conversation_message(
                normalized_id,
                sender="assistant",
                text=cleaned_text,
                direction="outgoing",
            )
            response = {
                "status": "sent",
                "action": "send_reply",
                "allowed": True,
                "sent": True,
                "conversation_id": conversation_id,
                "text": cleaned_text,
                "reason_code": "",
                "reason": "",
                "send_result": normalized_send_result,
            }
            if send_confirmer is not None:
                response["confirmed"] = True
            return response
        return {
            "status": "not_implemented",
            "action": "send_reply",
            "allowed": True,
            "conversation_id": conversation_id,
            "text": cleaned_text,
            "reason_code": "",
            "reason": "",
        }

    def validate_send_reply(self, conversation_id: str, text: str) -> dict[str, object]:
        normalized_id = str(conversation_id).strip()
        if not str(text).strip():
            return _blocked_send("EMPTY_TEXT", "回复内容不能为空。")
        control = self.get_conversation_control(normalized_id)
        if control["human_takeover"]:
            return _blocked_send("HUMAN_TAKEOVER", "该会话已由人工接管。")
        if control["paused"]:
            return _blocked_send("CONVERSATION_PAUSED", "该会话已暂停自动回复。")
        if control["blacklisted"]:
            return _blocked_send("BLACKLISTED", "该会话在黑名单中。")
        return {
            "allowed": True,
            "reason_code": "",
            "reason": "",
            "conversation_id": normalized_id,
        }

    def suggest_reply(self, conversation_id: str, message_text: str) -> ReplySuggestion:
        cleaned_text = str(message_text).strip()
        if not cleaned_text:
            return ReplySuggestion(conversation_id=conversation_id, input_text=message_text, suggestion="", status="empty_input")
        if self.reply_pipeline is None:
            suggestion = f"建议回复占位：{cleaned_text[:60]}"
            return ReplySuggestion(
                conversation_id=conversation_id,
                input_text=message_text,
                suggestion=suggestion,
                status="not_implemented",
            )
        detail = self.get_conversation(conversation_id)
        contexts = [
            str(item.get("text", ""))
            for item in detail.get("messages", [])
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ][-10:]
        message = Message(
            chat_id=conversation_id,
            chat_type=_conversation_chat_type(conversation_id),
            sender_name=_conversation_title_from_detail(detail) or conversation_id,
            text=cleaned_text,
            context=contexts,
            conversation_id=conversation_id,
        )
        suggestion = str(self.reply_pipeline.generate_reply(message)).strip()
        return ReplySuggestion(
            conversation_id=conversation_id,
            input_text=message_text,
            suggestion=suggestion,
            status="ready",
        )

    def list_conversations(self) -> list[ConversationListItem]:
        payload = self._load_conversation_payload()
        items: list[ConversationListItem] = []
        for conversation_id, record in payload.items():
            if not isinstance(record, dict):
                continue
            messages = record.get("messages", [])
            latest = messages[-1] if isinstance(messages, list) and messages else {}
            updated_at = str(latest.get("sent_at", "")) if isinstance(latest, dict) else None
            items.append(
                ConversationListItem(
                    conversation_id=conversation_id,
                    title=str(record.get("title", "")) or _conversation_title(conversation_id),
                    is_group=bool(record.get("is_group", conversation_id.startswith("group:"))),
                    latest_message=str(latest.get("text", "")) if isinstance(latest, dict) else "",
                    unread_count=int(record.get("unread_count", 0)),
                    updated_at=updated_at,
                )
            )
        return sorted(items, key=lambda item: item.updated_at or "", reverse=True)

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        normalized_id = str(conversation_id).strip()
        payload = self._load_conversation_payload()
        record = payload.get(normalized_id)
        if not isinstance(record, dict):
            record = {
                "title": _conversation_title(normalized_id),
                "is_group": normalized_id.startswith("group:"),
                "unread_count": 0,
                "messages": [],
            }
        messages = [
            _normalize_message_item(normalized_id, item)
            for item in record.get("messages", [])
            if isinstance(item, dict)
        ]
        conversation = ConversationListItem(
            conversation_id=normalized_id,
            title=str(record.get("title", "")) or _conversation_title(normalized_id),
            is_group=bool(record.get("is_group", normalized_id.startswith("group:"))),
            latest_message=str(messages[-1].get("text", "")) if messages else "",
            unread_count=int(record.get("unread_count", 0)),
            updated_at=str(messages[-1].get("sent_at", "")) if messages else None,
        )
        return {
            "conversation": asdict(conversation),
            "messages": messages,
            "control": self.get_conversation_control(normalized_id),
        }

    def record_conversation_message(
        self,
        conversation_id: str,
        *,
        sender: str,
        text: str,
        direction: str = "incoming",
        sent_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_id = str(conversation_id).strip()
        payload = self._load_conversation_payload()
        record = payload.get(normalized_id)
        if not isinstance(record, dict):
            record = {
                "title": str(sender).strip() or _conversation_title(normalized_id),
                "is_group": normalized_id.startswith("group:"),
                "unread_count": 0,
                "messages": [],
            }
        messages = record.get("messages")
        if not isinstance(messages, list):
            messages = []
        message = {
            "message_id": f"msg_{len(messages) + 1:04d}",
            "conversation_id": normalized_id,
            "sender": str(sender).strip() or "unknown",
            "text": str(text),
            "direction": direction if direction in {"incoming", "outgoing"} else "incoming",
            "sent_at": sent_at or utc_timestamp(),
        }
        messages.append(message)
        record["messages"] = messages[-100:]
        record["title"] = str(record.get("title", "")) or str(sender).strip() or _conversation_title(normalized_id)
        if message["direction"] == "incoming":
            record["unread_count"] = int(record.get("unread_count", 0)) + 1
        payload[normalized_id] = record
        self._save_conversation_payload(payload)
        return message

    def import_knowledge_files(self, file_paths: Sequence[Path | str]) -> dict[str, Any]:
        result = self.knowledge_importer.import_files(file_paths)
        return {
            "files": [asdict(item) for item in result.files],
            "index_status": asdict(result.index_status) if result.index_status is not None else self.get_knowledge_status(),
            "index_rebuilt": result.index_status is not None,
        }

    def search_knowledge(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        status = self.knowledge_importer.get_status()
        if not status.ready:
            return []
        retriever = LocalIndexRetriever(index_path=Path(status.index_path), embeddings=FakeEmbeddings())
        return [asdict(chunk) for chunk in retriever.retrieve(query, limit=limit)]

    def get_knowledge_status(self) -> dict[str, Any]:
        return asdict(self.knowledge_importer.get_status())

    def build_web_knowledge_from_documents(
        self,
        file_paths: Sequence[Path | str],
        *,
        search_limit: int = 5,
    ) -> dict[str, object]:
        return self.web_knowledge_builder.build_from_documents(file_paths, search_limit=search_limit)

    def get_recent_logs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        policy = self.get_privacy_policy()
        safe_limit = min(max(int(limit), 1), int(policy["max_recent_log_events"]))
        events = tail_jsonl_events(limit=safe_limit, path=self.runtime_log_path)
        if not policy["redact_sensitive_logs"]:
            return events
        return [_sanitize_event(event) for event in events]

    def get_privacy_policy(self) -> dict[str, Any]:
        return asdict(self.get_settings().privacy)

    def update_privacy_policy(self, patch: Mapping[str, object]) -> dict[str, Any]:
        settings = self.update_settings({"privacy": dict(patch)})
        return asdict(settings.privacy)

    def get_conversation_control(self, conversation_id: str) -> dict[str, object]:
        normalized_id = str(conversation_id).strip()
        settings = self.get_settings()
        return {
            "conversation_id": normalized_id,
            "human_takeover": normalized_id in settings.human_takeover_sessions,
            "paused": normalized_id in settings.paused_sessions,
            "whitelisted": normalized_id in settings.whitelist,
            "blacklisted": normalized_id in settings.blacklist,
        }

    def update_conversation_control(self, conversation_id: str, patch: Mapping[str, object]) -> dict[str, object]:
        normalized_id = str(conversation_id).strip()
        settings = self.get_settings()
        payload = {
            "human_takeover_sessions": _toggle_list(
                settings.human_takeover_sessions,
                normalized_id,
                patch.get("human_takeover"),
            ),
            "paused_sessions": _toggle_list(settings.paused_sessions, normalized_id, patch.get("paused")),
            "whitelist": _toggle_list(settings.whitelist, normalized_id, patch.get("whitelisted")),
            "blacklist": _toggle_list(settings.blacklist, normalized_id, patch.get("blacklisted")),
        }
        self.update_settings(payload)
        return self.get_conversation_control(normalized_id)

    def apply_retention_policy(self) -> dict[str, object]:
        policy = self.get_privacy_policy()
        logs_removed = self._prune_runtime_logs(retention_days=int(policy["log_retention_days"]))
        memory_files_trimmed = self._trim_memory_files()
        return {
            "logs_removed": logs_removed,
            "memory_files_trimmed": memory_files_trimmed,
            "log_retention_days": policy["log_retention_days"],
            "memory_retention_days": policy["memory_retention_days"],
        }

    def get_wechat_environment_status(self) -> dict[str, object]:
        wechat_path = locate_existing_wechat_path("")
        wechat_running = _is_wechat_running()
        ui_probe = self._probe_wechat_ui() if (wechat_running or self.wechat_window_probe is not None) else {
            "ready": "unknown",
            "status": "skipped",
            "reason": "未检测到微信进程，跳过窗口控件探测。",
        }
        return {
            "wechat_running": wechat_running,
            "wechat_path": wechat_path,
            "narrator_required": True,
            "ui_ready": ui_probe.get("ready", "unknown"),
            "ui_probe": ui_probe,
            "checks": [
                "wechat_process",
                "windows_accessibility",
                "display_scale",
                "foreground_permission",
            ],
        }

    def _get_wechat_window_probe(self) -> Any:
        if self.wechat_window_probe is None:
            self.wechat_window_probe = WeChatWindowProbe.from_pyweixin()
        return self.wechat_window_probe

    def _probe_wechat_ui(self) -> dict[str, object]:
        try:
            probe = self._get_wechat_window_probe()
            result = probe.probe_ui_ready()
        except Exception as exc:
            return {
                "ready": False,
                "status": "error",
                "reason": f"{type(exc).__name__}: {exc}",
            }
        if hasattr(result, "to_dict"):
            return dict(result.to_dict())
        if isinstance(result, Mapping):
            return dict(result)
        return {"ready": bool(result), "status": "ok" if result else "warn", "reason": ""}

    def _normalized_daemon_status(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if status.pid is not None and not self.daemon_runner.is_running(status.pid):
            status = self.daemon_controller.stop(now=datetime.now(timezone.utc))
        return asdict(status)

    def _load_conversation_payload(self) -> dict[str, Any]:
        if not self.conversation_store_path.exists():
            return {}
        try:
            payload = json.loads(self.conversation_store_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_conversation_payload(self, payload: Mapping[str, object]) -> None:
        self.conversation_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.conversation_store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _prune_runtime_logs(self, *, retention_days: int) -> int:
        if not self.runtime_log_path.exists():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - max(retention_days, 1) * 86400
        kept_lines: list[str] = []
        removed = 0
        with self.runtime_log_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    kept_lines.append(line if line.endswith("\n") else line + "\n")
                    continue
                timestamp = _parse_event_timestamp(event.get("timestamp"))
                if timestamp is not None and timestamp < cutoff:
                    removed += 1
                    continue
                kept_lines.append(json.dumps(event, ensure_ascii=False) + "\n")
        self.runtime_log_path.write_text("".join(kept_lines), encoding="utf-8")
        return removed

    def _trim_memory_files(self) -> int:
        memory_dir = self.data_root / "memory"
        if not memory_dir.exists():
            return 0
        trimmed = 0
        for path in memory_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            snapshots = payload.get("recent_conversation")
            if not isinstance(snapshots, list) or len(snapshots) <= 20:
                continue
            payload["recent_conversation"] = snapshots[-20:]
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            trimmed += 1
        return trimmed


def _sanitize_event(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, max_chars=500)
    if isinstance(value, dict):
        return {str(key): _sanitize_event(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_event(item) for item in value]
    return value


def _toggle_list(values: Sequence[str], item: str, desired: object) -> list[str]:
    result = [str(value) for value in values if str(value).strip()]
    if not item or desired is None:
        return result
    if desired is True and item not in result:
        result.append(item)
    if desired is False and item in result:
        result.remove(item)
    return result


def _conversation_chat_type(conversation_id: str) -> str:
    return "group" if str(conversation_id).startswith("group:") else "friend"


def _conversation_title(conversation_id: str) -> str:
    text = str(conversation_id).strip()
    if ":" in text:
        return text.split(":", 1)[1] or text
    return text


def _conversation_title_from_detail(detail: Mapping[str, object]) -> str:
    conversation = detail.get("conversation")
    if isinstance(conversation, Mapping):
        return str(conversation.get("title", "")).strip()
    return ""


def _confirmation_succeeded(value: object) -> bool:
    if isinstance(value, Mapping):
        return bool(value.get("confirmed", value.get("sent", False)))
    return bool(value)


def _normalize_message_item(conversation_id: str, item: Mapping[str, object]) -> dict[str, object]:
    return {
        "message_id": str(item.get("message_id", "")) or "msg_unknown",
        "conversation_id": str(item.get("conversation_id", "")) or conversation_id,
        "sender": str(item.get("sender", "")) or "unknown",
        "text": str(item.get("text", "")),
        "direction": str(item.get("direction", "incoming")) if item.get("direction") in {"incoming", "outgoing"} else "incoming",
        "sent_at": str(item.get("sent_at", "")),
    }


def _blocked_send(reason_code: str, reason: str) -> dict[str, object]:
    return {
        "allowed": False,
        "reason_code": reason_code,
        "reason": reason,
    }


def _parse_event_timestamp(value: object) -> float | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text).astimezone(timezone.utc).timestamp()
    except ValueError:
        return None


def _is_wechat_running() -> bool:
    return is_process_running("Weixin.exe") or is_process_running("WeChat.exe")
