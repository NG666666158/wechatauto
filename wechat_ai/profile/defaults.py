from __future__ import annotations

from pathlib import Path

from ..paths import AGENTS_DIR, USERS_DIR


DEFAULT_ACTIVE_AGENT_ID = "default_assistant"
DEFAULT_PROFILE_AUTO_CREATE = True

DEFAULT_FRIEND_SYSTEM_PROMPT = (
    "你是微信单聊自动回复助手。请结合最近聊天上下文，用自然、简洁、符合真人聊天习惯的中文回复。"
    "不要编造事实，不确定时直接说明。除非用户明确要求，否则不要输出长篇大论。"
)

DEFAULT_GROUP_SYSTEM_PROMPT = (
    "你是微信群聊中被@时的自动回复助手。请结合最近聊天上下文，只回应和当前@相关的内容。"
    "回复要简洁、克制、避免刷屏，不要连续追问，不要偏题。"
)

DEFAULT_FALLBACK_REPLY = "我这边暂时没法完整回复，稍后再回你。"


def default_user_profile_dir() -> Path:
    return USERS_DIR


def default_agent_profile_dir() -> Path:
    return AGENTS_DIR
