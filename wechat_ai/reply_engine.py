from __future__ import annotations

from dataclasses import dataclass

from .context import render_context_block


@dataclass(slots=True)
class ScenePrompts:
    friend_system_prompt: str
    group_system_prompt: str


class ReplyEngine:
    def __init__(self, provider, prompts: ScenePrompts, context_limit: int = 10, model: str | None = None) -> None:
        self.provider = provider
        self.prompts = prompts
        self.context_limit = context_limit
        self.model = model

    def generate_friend_reply(self, latest_message: str, contexts: list[str]) -> str:
        user_prompt = self._build_user_prompt(scene="friend", latest_message=latest_message, contexts=contexts)
        return self.provider.complete(
            system_prompt=self.prompts.friend_system_prompt,
            user_prompt=user_prompt,
            model=self.model,
        )

    def generate_group_reply(self, latest_message: str, contexts: list[str]) -> str:
        user_prompt = self._build_user_prompt(scene="group", latest_message=latest_message, contexts=contexts)
        return self.provider.complete(
            system_prompt=self.prompts.group_system_prompt,
            user_prompt=user_prompt,
            model=self.model,
        )

    def _build_user_prompt(self, scene: str, latest_message: str, contexts: list[str]) -> str:
        return (
            f"场景: {scene}\n"
            f"最近{self.context_limit}条上下文:\n{render_context_block(contexts, limit=self.context_limit)}\n\n"
            f"当前需要回复的最新消息:\n{latest_message}\n\n"
            "请直接输出适合发回微信的中文回复正文，不要附加解释。"
        )
