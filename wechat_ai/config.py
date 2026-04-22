from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .paths import AGENTS_DIR, USERS_DIR
from .profile.defaults import (
    DEFAULT_ACTIVE_AGENT_ID,
    DEFAULT_FALLBACK_REPLY,
    DEFAULT_FRIEND_SYSTEM_PROMPT,
    DEFAULT_GROUP_SYSTEM_PROMPT,
    DEFAULT_PROFILE_AUTO_CREATE,
    default_agent_profile_dir,
    default_user_profile_dir,
)


@dataclass(slots=True)
class MiniMaxSettings:
    api_key: str
    model: str = "MiniMax-M2.5"
    api_url: str = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "MiniMaxSettings":
        api_key = os.getenv("MINIMAX_API_KEY", "").strip()
        if not api_key:
            raise ValueError("MINIMAX_API_KEY is required")
        model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5").strip() or "MiniMax-M2.5"
        api_url = os.getenv("MINIMAX_API_URL", "https://api.minimaxi.com/v1/text/chatcompletion_v2").strip()
        timeout = int(os.getenv("MINIMAX_TIMEOUT", "30"))
        return cls(api_key=api_key, model=model, api_url=api_url, timeout=timeout)


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class ProfileSettings:
    default_active_agent_id: str = DEFAULT_ACTIVE_AGENT_ID
    user_profile_dir: Path = default_user_profile_dir()
    agent_profile_dir: Path = default_agent_profile_dir()
    profile_auto_create: bool = DEFAULT_PROFILE_AUTO_CREATE

    @classmethod
    def from_env(cls) -> "ProfileSettings":
        default_active_agent_id = os.getenv(
            "WECHAT_ACTIVE_AGENT_ID",
            DEFAULT_ACTIVE_AGENT_ID,
        ).strip() or DEFAULT_ACTIVE_AGENT_ID
        user_profile_dir = Path(
            os.getenv("WECHAT_USER_PROFILE_DIR", str(default_user_profile_dir()))
        )
        agent_profile_dir = Path(
            os.getenv("WECHAT_AGENT_PROFILE_DIR", str(default_agent_profile_dir()))
        )
        return cls(
            default_active_agent_id=default_active_agent_id,
            user_profile_dir=user_profile_dir,
            agent_profile_dir=agent_profile_dir,
            profile_auto_create=_env_flag(
                "WECHAT_PROFILE_AUTO_CREATE",
                DEFAULT_PROFILE_AUTO_CREATE,
            ),
        )


@dataclass(slots=True)
class ReplySettings:
    context_limit: int = 10
    friend_system_prompt: str = DEFAULT_FRIEND_SYSTEM_PROMPT
    group_system_prompt: str = DEFAULT_GROUP_SYSTEM_PROMPT
    fallback_reply: str = DEFAULT_FALLBACK_REPLY
    group_mention_names: tuple[str, ...] = ()
    prompt_preview_max_chars: int = 400

    @classmethod
    def from_env(cls) -> "ReplySettings":
        names = tuple(
            item.strip()
            for item in os.getenv("WECHAT_GROUP_MENTION_NAMES", "").split(",")
            if item.strip()
        )
        return cls(
            context_limit=int(os.getenv("WECHAT_CONTEXT_LIMIT", "10")),
            friend_system_prompt=os.getenv("WECHAT_FRIEND_SYSTEM_PROMPT", DEFAULT_FRIEND_SYSTEM_PROMPT),
            group_system_prompt=os.getenv("WECHAT_GROUP_SYSTEM_PROMPT", DEFAULT_GROUP_SYSTEM_PROMPT),
            fallback_reply=os.getenv("WECHAT_REPLY_FALLBACK", DEFAULT_FALLBACK_REPLY),
            group_mention_names=names,
            prompt_preview_max_chars=int(os.getenv("WECHAT_PROMPT_PREVIEW_MAX_CHARS", "400")),
        )
