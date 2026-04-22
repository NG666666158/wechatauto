from __future__ import annotations

from collections.abc import Mapping

from wechat_ai.logging_utils import JsonlEventLogger, sanitize_text
from wechat_ai.models import Message
from wechat_ai.orchestration.context_manager import ContextManager
from wechat_ai.orchestration.message_parser import MessageParser
from wechat_ai.reply_engine import ReplyEngine, ScenePrompts


class ReplyPipeline:
    """Orchestrates profile/context/retrieval inputs before calling the reply engine."""

    def __init__(
        self,
        provider,
        prompts: ScenePrompts,
        context_limit: int = 10,
        model: str | None = None,
        *,
        profile_store=None,
        active_agent_id: str = "default_assistant",
        context_manager: ContextManager | None = None,
        retriever=None,
        reply_engine: ReplyEngine | None = None,
        retrieval_limit: int = 3,
        memory_store=None,
        event_logger=None,
        prompt_preview_max_chars: int = 400,
    ) -> None:
        self.provider = provider
        self.prompts = prompts
        self.context_limit = context_limit
        self.model = model
        self.profile_store = profile_store
        self.active_agent_id = active_agent_id
        self.context_manager = context_manager or ContextManager(max_messages=context_limit)
        self.retriever = retriever
        self.retrieval_limit = retrieval_limit
        self.memory_store = memory_store
        self.event_logger = event_logger or JsonlEventLogger()
        self.prompt_preview_max_chars = prompt_preview_max_chars
        self._engine = reply_engine or ReplyEngine(
            provider=provider,
            prompts=prompts,
            context_limit=context_limit,
            model=model,
        )

    def generate_reply(self, message: Message | Mapping[str, object] | object) -> str:
        normalized = self._coerce_message(message)
        self._log_event(
            "message_received",
            chat_id=normalized.chat_id,
            chat_type=normalized.chat_type,
            sender_name=normalized.sender_name,
            message_preview=self._preview_text(normalized.text),
            context_count=len(normalized.context),
        )
        user_profile = self._load_user_profile(normalized)
        agent_profile = self._load_agent_profile()
        prepared_message = self.context_manager.prepare_message(normalized)
        knowledge_chunks = self._retrieve_knowledge(prepared_message.text)
        memory_summary = self._load_memory_summary(prepared_message.chat_id)
        prompt_preview = self._build_prompt_preview(
            prepared_message=prepared_message,
            agent_profile=agent_profile,
            user_profile=user_profile,
            knowledge_chunks=knowledge_chunks,
            memory_summary=memory_summary,
        )
        self._log_event(
            "prompt_built",
            chat_id=prepared_message.chat_id,
            chat_type=prepared_message.chat_type,
            prompt_preview=self._preview_text(prompt_preview),
            prompt_preview_max_chars=self.prompt_preview_max_chars,
        )
        if prepared_message.chat_type == "group":
            reply = self._engine.generate_group_reply(
                latest_message=prepared_message.text,
                contexts=prepared_message.context,
                agent_profile=agent_profile,
                user_profile=user_profile,
                knowledge_chunks=knowledge_chunks,
                memory_summary=memory_summary,
            )
        else:
            reply = self._engine.generate_friend_reply(
                latest_message=prepared_message.text,
                contexts=prepared_message.context,
                agent_profile=agent_profile,
                user_profile=user_profile,
                knowledge_chunks=knowledge_chunks,
                memory_summary=memory_summary,
            )
        self._log_event(
            "model_completed",
            chat_id=prepared_message.chat_id,
            chat_type=prepared_message.chat_type,
            reply_preview=self._preview_text(reply),
            used_fallback=False,
        )
        self._append_memory_snapshot(
            chat_id=prepared_message.chat_id,
            contexts=prepared_message.context,
            latest_message=prepared_message.text,
            reply=reply,
        )
        return reply

    def generate_friend_reply(self, latest_message: str, contexts: list[str]) -> str:
        return self.generate_reply(
            MessageParser.parse_friend_message(
                chat_id="friend",
                text=latest_message,
                contexts=contexts,
            )
        )

    def generate_group_reply(self, latest_message: str, contexts: list[str]) -> str:
        return self.generate_reply(
            MessageParser.parse_group_message(
                chat_id="group",
                sender_name="group_member",
                text=latest_message,
                contexts=contexts,
            )
        )

    def _coerce_message(self, message: Message | Mapping[str, object] | object) -> Message:
        if isinstance(message, Message):
            return message
        if isinstance(message, Mapping):
            values = message
        else:
            values = {
                "chat_id": getattr(message, "chat_id", ""),
                "chat_type": getattr(message, "chat_type", ""),
                "sender_name": getattr(message, "sender_name", ""),
                "text": getattr(message, "text", ""),
                "timestamp": getattr(message, "timestamp", None),
                "context": getattr(message, "context", []),
            }
        chat_type = str(values.get("chat_type", "friend")).strip() or "friend"
        if chat_type == "group":
            return MessageParser.parse_group_message(
                chat_id=str(values.get("chat_id", "")),
                sender_name=str(values.get("sender_name", "")),
                text=str(values.get("text", "")),
                contexts=values.get("context"),
                timestamp=self._optional_text(values.get("timestamp")),
            )
        return MessageParser.parse_friend_message(
            chat_id=str(values.get("chat_id", "")),
            text=str(values.get("text", "")),
            contexts=values.get("context"),
            sender_name=self._optional_text(values.get("sender_name")),
            timestamp=self._optional_text(values.get("timestamp")),
        )

    def _load_user_profile(self, message: Message):
        if self.profile_store is None:
            return None
        user_id = message.chat_id if message.chat_type == "friend" else message.sender_name or message.chat_id
        if not user_id:
            return None
        profile = self.profile_store.load_user_profile(user_id)
        self._log_event(
            "profile_loaded",
            profile_kind="user",
            profile_id=user_id,
            chat_id=message.chat_id,
        )
        return profile

    def _load_agent_profile(self):
        if self.profile_store is None or not self.active_agent_id:
            return None
        profile = self.profile_store.load_agent_profile(self.active_agent_id)
        self._log_event(
            "profile_loaded",
            profile_kind="agent",
            profile_id=self.active_agent_id,
        )
        return profile

    def _retrieve_knowledge(self, query: str) -> list[str]:
        if self.retriever is None or not query.strip():
            return []
        chunks = self.retriever.retrieve(query, limit=self.retrieval_limit)
        normalized: list[str] = []
        for chunk in chunks:
            text = getattr(chunk, "text", chunk)
            cleaned = str(text).strip()
            if cleaned:
                normalized.append(cleaned)
        self._log_event(
            "retrieval_completed",
            query_preview=self._preview_text(query),
            result_count=len(normalized),
        )
        return normalized

    def _load_memory_summary(self, chat_id: str) -> str | None:
        if self.memory_store is None or not chat_id.strip():
            return None
        return self.memory_store.load_summary_text(chat_id)

    def _append_memory_snapshot(
        self,
        *,
        chat_id: str,
        contexts: list[str],
        latest_message: str,
        reply: str,
    ) -> None:
        if self.memory_store is None or not chat_id.strip():
            return
        snapshot_messages = [*contexts, latest_message, reply]
        self.memory_store.append_snapshot(chat_id, snapshot_messages)

    def _build_prompt_preview(
        self,
        *,
        prepared_message: Message,
        agent_profile,
        user_profile,
        knowledge_chunks: list[str],
        memory_summary: str | None,
    ) -> str:
        return self._engine.prompt_builder.debug_preview(
            scene=prepared_message.chat_type,
            latest_message=prepared_message.text,
            contexts=prepared_message.context,
            agent_profile=agent_profile,
            user_profile=user_profile,
            knowledge_chunks=knowledge_chunks,
            memory_summary=memory_summary,
        )

    def _log_event(self, event_type: str, **fields: object) -> None:
        if self.event_logger is None:
            return
        self.event_logger.log_event(event_type, **fields)

    def _preview_text(self, value: object) -> str:
        return sanitize_text(value, max_chars=self.prompt_preview_max_chars)

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
