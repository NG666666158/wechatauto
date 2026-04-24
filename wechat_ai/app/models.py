from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkHours:
    enabled: bool = True
    start: str = "09:00"
    end: str = "18:00"


@dataclass(slots=True)
class ScheduleBlock:
    day_of_week: str
    start: str
    end: str
    label: str = ""
    enabled: bool = True


@dataclass(slots=True)
class SettingsSnapshot:
    auto_reply_enabled: bool = True
    reply_style: str = "自然友好"
    new_customer_auto_create: bool = True
    sensitive_message_review: bool = True
    work_hours: WorkHours = field(default_factory=WorkHours)
    knowledge_chunk_size: int = 1000
    knowledge_chunk_overlap: int = 200
    run_silently: bool = True
    esc_action: str = "pause"
    schedule_enabled: bool = False
    schedule_blocks: list[ScheduleBlock] = field(default_factory=list)


@dataclass(slots=True)
class AppStatus:
    wechat_status: str = "unknown"
    daemon_state: str = "stopped"
    auto_reply_enabled: bool = True
    today_received: int = 0
    today_replied: int = 0
    pending_count: int = 0
    knowledge_index_ready: bool = False
    last_heartbeat: str | None = None


@dataclass(slots=True)
class DaemonStatus:
    state: str = "stopped"
    pid: int | None = None
    run_silently: bool = True
    last_heartbeat: str | None = None
    last_started_at: str | None = None
    last_stopped_at: str | None = None
    last_error: str | None = None
    consecutive_errors: int = 0
    retry_backoff_seconds: float = 0.0
    next_retry_at: str | None = None
    today_received: int = 0
    today_replied: int = 0


@dataclass(slots=True)
class ScheduleStatus:
    enabled: bool = False
    should_run: bool = True
    active_block_label: str = ""
    active_block_day: str = ""
    next_action: str = "none"
    next_transition_at: str | None = None
    reason: str = "schedule_disabled"


@dataclass(slots=True)
class TrayMenuItem:
    item_id: str
    label: str
    action: str
    enabled: bool = True


@dataclass(slots=True)
class TrayState:
    tooltip: str
    menu_items: list[TrayMenuItem] = field(default_factory=list)
    recommended_action: str = "show_window"


@dataclass(slots=True)
class ConversationListItem:
    conversation_id: str
    title: str
    is_group: bool = False
    latest_message: str = ""
    unread_count: int = 0
    updated_at: str | None = None


@dataclass(slots=True)
class ConversationMessageItem:
    message_id: str
    conversation_id: str
    sender: str
    text: str
    direction: str = "incoming"
    sent_at: str | None = None


@dataclass(slots=True)
class ReplySuggestion:
    conversation_id: str
    input_text: str
    suggestion: str
    status: str = "ready"


@dataclass(slots=True)
class KnowledgeFileRecord:
    file_id: str
    file_name: str
    source_path: str
    stored_path: str
    extension: str
    status: str
    size_bytes: int = 0
    error_message: str | None = None


@dataclass(slots=True)
class KnowledgeIndexStatus:
    ready: bool
    index_path: str
    documents_loaded: int = 0
    chunks_created: int = 0
    last_built_at: str | None = None
    embedding_provider: str | None = None
    supported_extensions: tuple[str, ...] = (".json", ".md", ".txt")


@dataclass(slots=True)
class CustomerRecord:
    customer_id: str
    display_name: str
    status: str
    tags: list[str] = field(default_factory=list)
    remark: str = ""
    last_contact_at: str | None = None
