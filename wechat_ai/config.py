from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_FRIEND_SYSTEM_PROMPT = (
    "你是微信单聊自动回复助手。请结合最近聊天上下文，用自然、简洁、符合真人聊天习惯的中文回复。"
    "不要编造事实，不确定时直接说明。除非用户明确要求，否则不要输出长篇大论。"
)

DEFAULT_GROUP_SYSTEM_PROMPT = (
    "你是微信群聊中被@时的自动回复助手。请结合最近聊天上下文，只回应和当前@相关的内容。"
    "回复要简洁、克制、避免刷屏，不要连续追问，不要偏题。"
)

DEFAULT_FALLBACK_REPLY = "我这边暂时没法完整回复，稍后再回你。"


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


@dataclass(slots=True)
class ReplySettings:
    context_limit: int = 10
    friend_system_prompt: str = DEFAULT_FRIEND_SYSTEM_PROMPT
    group_system_prompt: str = DEFAULT_GROUP_SYSTEM_PROMPT
    fallback_reply: str = DEFAULT_FALLBACK_REPLY
    group_mention_names: tuple[str, ...] = ()

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
        )
