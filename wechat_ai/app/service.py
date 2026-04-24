from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from wechat_ai import paths
from wechat_ai.identity import identity_admin
from wechat_ai.rag.embeddings import FakeEmbeddings
from wechat_ai.rag.retriever import LocalIndexRetriever
from wechat_ai.rag.web_knowledge_builder import WebKnowledgeBuilder
from wechat_ai.self_identity import admin as self_identity_admin

from .daemon_controller import DaemonController
from .knowledge_importer import KnowledgeImporter
from .models import AppStatus, CustomerRecord, ReplySuggestion
from .schedule_manager import ScheduleManager
from .settings_store import DesktopSettingsStore
from .tray_adapter import TrayAdapter


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
    ) -> int:
        del run_silently, poll_interval, heartbeat_interval, error_backoff_seconds
        pid = self._next_pid
        self._next_pid += 1
        self._running.add(pid)
        return pid

    def stop(self, pid: int) -> bool:
        self._running.discard(pid)
        return True

    def is_running(self, pid: int | None) -> bool:
        return pid is not None and pid in self._running


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
    ) -> None:
        root = Path(data_root) if data_root is not None else paths.DATA_DIR
        self.data_root = root
        self.app_dir = root / "app"
        self.identity_dir = root / "identity"
        self.self_identity_dir = root / "self_identity"
        self.settings_store = settings_store or DesktopSettingsStore(self.app_dir / "desktop_settings.json")
        self.daemon_controller = DaemonController(self.app_dir / "daemon_state.json")
        self.daemon_runner = daemon_runner or _NoOpDaemonRunner()
        self.schedule_manager = ScheduleManager()
        self.tray_adapter = TrayAdapter()
        self.knowledge_importer = knowledge_importer or KnowledgeImporter(
            knowledge_dir=root / "knowledge",
            uploads_dir=root / "knowledge" / "uploads",
            index_path=root / "knowledge" / "local_knowledge_index.json",
        )
        self.web_knowledge_builder = web_knowledge_builder or WebKnowledgeBuilder(
            knowledge_dir=root / "knowledge",
            knowledge_importer=self.knowledge_importer,
        )
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
        pid = self.daemon_runner.launch(
            run_silently=settings.run_silently,
            poll_interval=1.0,
            heartbeat_interval=60.0,
            error_backoff_seconds=5.0,
        )
        status = self.daemon_controller.start(run_silently=settings.run_silently, pid=pid)
        return asdict(status)

    def pause_daemon(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if status.pid is not None:
            self.daemon_runner.stop(status.pid)
        updated = self.daemon_controller.pause()
        updated.pid = status.pid
        self.daemon_controller._save(updated)
        return asdict(updated)

    def stop_daemon(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if status.pid is not None:
            self.daemon_runner.stop(status.pid)
        updated = self.daemon_controller.stop()
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
        return {"status": "not_implemented", "action": "send_reply", "conversation_id": conversation_id, "text": text}

    def suggest_reply(self, conversation_id: str, message_text: str) -> ReplySuggestion:
        suggestion = f"建议回复占位：{message_text.strip()[:60]}" if message_text.strip() else ""
        return ReplySuggestion(
            conversation_id=conversation_id,
            input_text=message_text,
            suggestion=suggestion,
            status="not_implemented",
        )

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

    def _normalized_daemon_status(self) -> dict[str, object]:
        status = self.daemon_controller.load_status()
        if status.pid is not None and not self.daemon_runner.is_running(status.pid):
            status = self.daemon_controller.stop(now=datetime.now(timezone.utc))
        return asdict(status)
