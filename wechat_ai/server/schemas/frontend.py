from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeImportRequest(StrictRequestModel):
    file_paths: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("file_paths", mode="after")
    @classmethod
    def reject_blank_file_paths(cls, value: list[str]) -> list[str]:
        return _clean_nonblank_strings(value, field_name="file_paths")


class WebKnowledgeBuildRequest(StrictRequestModel):
    file_paths: list[str] = Field(..., min_length=1, max_length=20)
    search_limit: int = Field(5, ge=1, le=20)

    @field_validator("file_paths", mode="after")
    @classmethod
    def reject_blank_file_paths(cls, value: list[str]) -> list[str]:
        return _clean_nonblank_strings(value, field_name="file_paths")


class ReplySuggestionRequest(StrictRequestModel):
    message_text: str = Field("", max_length=8000)


class SendReplyRequest(StrictRequestModel):
    text: str = Field("", max_length=8000)


class PrivacyPolicyPatchRequest(StrictRequestModel):
    redact_sensitive_logs: bool | None = None
    log_retention_days: int | None = Field(None, ge=1, le=365)
    memory_retention_days: int | None = Field(None, ge=1, le=3650)
    max_recent_log_events: int | None = Field(None, ge=1, le=5000)


class WorkHoursPatchRequest(StrictRequestModel):
    enabled: bool | None = None
    start: str | None = Field(None, min_length=4, max_length=5)
    end: str | None = Field(None, min_length=4, max_length=5)


class ScheduleBlockPatchRequest(StrictRequestModel):
    day_of_week: str | None = Field(None, max_length=16)
    start: str | None = Field(None, min_length=4, max_length=5)
    end: str | None = Field(None, min_length=4, max_length=5)
    label: str | None = Field(None, max_length=64)
    enabled: bool | None = None


class SettingsPatchRequest(StrictRequestModel):
    auto_reply_enabled: bool | None = None
    reply_style: str | None = Field(None, max_length=64)
    new_customer_auto_create: bool | None = None
    sensitive_message_review: bool | None = None
    work_hours: WorkHoursPatchRequest | None = None
    knowledge_chunk_size: int | None = Field(None, ge=100, le=20000)
    knowledge_chunk_overlap: int | None = Field(None, ge=0, le=5000)
    run_silently: bool | None = None
    esc_action: str | None = Field(None, max_length=32)
    schedule_enabled: bool | None = None
    schedule_blocks: list[ScheduleBlockPatchRequest] | None = Field(None, max_length=32)
    privacy: PrivacyPolicyPatchRequest | None = None
    human_takeover_sessions: list[str] | None = Field(None, max_length=500)
    paused_sessions: list[str] | None = Field(None, max_length=500)
    whitelist: list[str] | None = Field(None, max_length=500)
    blacklist: list[str] | None = Field(None, max_length=500)
    request_timeout_seconds: float | None = Field(None, ge=1, le=300)
    retry_attempts: int | None = Field(None, ge=0, le=10)
    real_send_enabled: bool | None = None


class ConversationControlPatchRequest(StrictRequestModel):
    human_takeover: bool | None = None
    paused: bool | None = None
    whitelisted: bool | None = None
    blacklisted: bool | None = None


class SelfIdentityPatchRequest(StrictRequestModel):
    display_name: str | None = Field(None, min_length=1, max_length=64)
    identity_facts: list[str] | None = Field(None, max_length=100)

    @field_validator("identity_facts", mode="after")
    @classmethod
    def reject_blank_identity_facts(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_nonblank_strings(value, field_name="identity_facts")


def _clean_nonblank_strings(value: list[str], *, field_name: str) -> list[str]:
    cleaned = [item.strip() for item in value]
    if any(not item for item in cleaned):
        raise ValueError(f"{field_name} must not contain blank values")
    return cleaned
