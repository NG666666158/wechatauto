from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(default="global")


class DaemonStatusData(BaseModel):
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


class AppStatusData(BaseModel):
    wechat_status: str = "unknown"
    daemon_state: str = "stopped"
    auto_reply_enabled: bool = True
    today_received: int = 0
    today_replied: int = 0
    pending_count: int = 0
    knowledge_index_ready: bool = False
    last_heartbeat: str | None = None


class RuntimeStatusData(BaseModel):
    state: str = "stopped"
    mode: str = "global"
    running: bool = False
    daemon: DaemonStatusData = Field(default_factory=DaemonStatusData)
    app: AppStatusData | dict[str, Any] = Field(default_factory=AppStatusData)


class RuntimeActionData(BaseModel):
    state: str = "stopped"
    mode: str = "global"
    running: bool = False
    daemon: DaemonStatusData = Field(default_factory=DaemonStatusData)
