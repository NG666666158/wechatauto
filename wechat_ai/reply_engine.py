from __future__ import annotations

from dataclasses import dataclass

from .orchestration.prompt_builder import PromptBuilder


@dataclass(slots=True)
class ScenePrompts:
    friend_system_prompt: str
    group_system_prompt: str


class ReplyEngine:
    def __init__(
        self,
        provider,
        prompts: ScenePrompts,
        context_limit: int = 10,
        model: str | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.provider = provider
        self.prompts = prompts
        self.context_limit = context_limit
        self.model = model
        self.prompt_builder = prompt_builder or PromptBuilder(context_limit=context_limit)

    def generate_friend_reply(
        self,
        latest_message: str,
        contexts: list[str],
        *,
        agent_profile=None,
        user_profile=None,
        knowledge_chunks: list[str] | None = None,
        memory_summary: str | None = None,
    ) -> str:
        user_prompt = self._build_user_prompt(
            scene="friend",
            latest_message=latest_message,
            contexts=contexts,
            agent_profile=agent_profile,
            user_profile=user_profile,
            knowledge_chunks=knowledge_chunks,
            memory_summary=memory_summary,
        )
        return self.provider.complete(
            system_prompt=self.prompts.friend_system_prompt,
            user_prompt=user_prompt,
            model=self.model,
        )

    def generate_group_reply(
        self,
        latest_message: str,
        contexts: list[str],
        *,
        agent_profile=None,
        user_profile=None,
        knowledge_chunks: list[str] | None = None,
        memory_summary: str | None = None,
    ) -> str:
        user_prompt = self._build_user_prompt(
            scene="group",
            latest_message=latest_message,
            contexts=contexts,
            agent_profile=agent_profile,
            user_profile=user_profile,
            knowledge_chunks=knowledge_chunks,
            memory_summary=memory_summary,
        )
        return self.provider.complete(
            system_prompt=self.prompts.group_system_prompt,
            user_prompt=user_prompt,
            model=self.model,
        )

    def _build_user_prompt(
        self,
        scene: str,
        latest_message: str,
        contexts: list[str],
        *,
        agent_profile=None,
        user_profile=None,
        knowledge_chunks: list[str] | None = None,
        memory_summary: str | None = None,
    ) -> str:
        return self.prompt_builder.render_prompt(
            scene=scene,
            latest_message=latest_message,
            contexts=contexts,
            agent_profile=agent_profile,
            user_profile=user_profile,
            knowledge_chunks=knowledge_chunks,
            memory_summary=memory_summary,
        )
