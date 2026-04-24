from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .runtime import AppStatusData, RuntimeStatusData


class KnowledgeStatusData(BaseModel):
    ready: bool = False
    index_path: str = ""
    documents_loaded: int = 0
    chunks_created: int = 0
    last_built_at: str | None = None
    embedding_provider: str | None = None
    supported_extensions: list[str] | tuple[str, ...] = Field(default_factory=list)


class DashboardPendingData(BaseModel):
    identity_drafts: int = 0
    identity_candidates: int = 0


class DashboardSummaryData(BaseModel):
    app: AppStatusData | dict[str, Any] = Field(default_factory=AppStatusData)
    runtime: RuntimeStatusData = Field(default_factory=RuntimeStatusData)
    knowledge: KnowledgeStatusData | dict[str, Any] = Field(default_factory=KnowledgeStatusData)
    pending: DashboardPendingData = Field(default_factory=DashboardPendingData)


class WorkHoursData(BaseModel):
    enabled: bool = True
    start: str = "09:00"
    end: str = "18:00"


class ScheduleBlockData(BaseModel):
    day_of_week: str = ""
    start: str = ""
    end: str = ""
    label: str = ""
    enabled: bool = True


class PrivacyPolicyData(BaseModel):
    redact_sensitive_logs: bool = True
    log_retention_days: int = 14
    memory_retention_days: int = 90
    max_recent_log_events: int = 100


class SettingsData(BaseModel):
    auto_reply_enabled: bool = True
    reply_style: str = ""
    new_customer_auto_create: bool = True
    sensitive_message_review: bool = True
    work_hours: WorkHoursData = Field(default_factory=WorkHoursData)
    knowledge_chunk_size: int = 1000
    knowledge_chunk_overlap: int = 200
    run_silently: bool = True
    esc_action: str = "pause"
    schedule_enabled: bool = False
    schedule_blocks: list[ScheduleBlockData] = Field(default_factory=list)
    privacy: PrivacyPolicyData = Field(default_factory=PrivacyPolicyData)
    human_takeover_sessions: list[str] = Field(default_factory=list)
    paused_sessions: list[str] = Field(default_factory=list)
    whitelist: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(default_factory=list)
    request_timeout_seconds: float = 30.0
    retry_attempts: int = 2
    real_send_enabled: bool = False


class LogsSummaryData(BaseModel):
    recent_count: int = 0
    recent_error_count: int = 0
    last_event_time: str | None = None


class ConversationListItemData(BaseModel):
    conversation_id: str = ""
    title: str = ""
    is_group: bool = False
    latest_message: str = ""
    unread_count: int = 0
    updated_at: str | None = None


class ConversationMessageData(BaseModel):
    message_id: str = ""
    conversation_id: str = ""
    sender: str = ""
    text: str = ""
    direction: str = "incoming"
    sent_at: str | None = None


class ConversationControlData(BaseModel):
    conversation_id: str = ""
    human_takeover: bool = False
    paused: bool = False
    whitelisted: bool = False
    blacklisted: bool = False


class ConversationDetailData(BaseModel):
    conversation: ConversationListItemData = Field(default_factory=ConversationListItemData)
    messages: list[ConversationMessageData] = Field(default_factory=list)
    control: ConversationControlData = Field(default_factory=ConversationControlData)


class ReplySuggestionData(BaseModel):
    conversation_id: str = ""
    input_text: str = ""
    suggestion: str = ""
    status: str = "ready"


class SendReplyResultData(BaseModel):
    status: str = ""
    allowed: bool = False
    conversation_id: str = ""
    text: str = ""
    reason_code: str = ""
    reason: str = ""


class CustomerData(BaseModel):
    customer_id: str = ""
    display_name: str = ""
    status: str = ""
    tags: list[str] = Field(default_factory=list)
    remark: str = ""
    last_contact_at: str | None = None


class IdentityDraftData(BaseModel):
    draft_user_id: str = ""


class IdentityCandidateData(BaseModel):
    candidate_id: str = ""


class SelfIdentityData(BaseModel):
    display_name: str = ""
    identity_facts: list[str] = Field(default_factory=list)


class KnowledgeSearchResultData(BaseModel):
    chunk_id: str = ""
    text: str = ""
    score: float = 0.0


class KnowledgeFileImportData(BaseModel):
    file_name: str = ""
    status: str = ""


class KnowledgeImportResultData(BaseModel):
    files: list[KnowledgeFileImportData] = Field(default_factory=list)
    index_rebuilt: bool = False


class WebKnowledgeBuildResultData(BaseModel):
    documents: list[str] = Field(default_factory=list)
    search_limit: int = 5
    status: str = ""


class RetentionApplyResultData(BaseModel):
    logs_removed: int = 0
    memory_files_trimmed: int = 0


class WechatEnvironmentData(BaseModel):
    wechat_running: bool = False
    narrator_required: bool = False
    ui_ready: str | bool = "unknown"
