from __future__ import annotations

from collections.abc import Mapping

from wechat_ai.logging_utils import JsonlEventLogger, sanitize_text
from wechat_ai.models import Message
from wechat_ai.orchestration.context_manager import ContextManager
from wechat_ai.orchestration.message_parser import MessageParser
from wechat_ai.reply_engine import ReplyEngine, ScenePrompts
from wechat_ai.self_identity import SelfIdentityResolver


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
        self_identity_resolver: SelfIdentityResolver | None = None,
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
        self.self_identity_resolver = self_identity_resolver
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
        prepared_message = self._merge_message_metadata(
            normalized,
            self.context_manager.prepare_message(normalized),
        )
        self_identity_profile = self._load_self_identity_profile(
            message=prepared_message,
            user_profile=user_profile,
            agent_profile=agent_profile,
        )
        knowledge_chunks = self._retrieve_knowledge(prepared_message.text)
        memory_summary = self._load_memory_summary(prepared_message)
        prompt_preview = self._build_prompt_preview(
            prepared_message=prepared_message,
            agent_profile=agent_profile,
            user_profile=user_profile,
            self_identity_profile=self_identity_profile,
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
                self_identity_profile=self_identity_profile,
                self_identity=self_identity_profile,
                knowledge_chunks=knowledge_chunks,
                memory_summary=memory_summary,
            )
        else:
            reply = self._engine.generate_friend_reply(
                latest_message=prepared_message.text,
                contexts=prepared_message.context,
                agent_profile=agent_profile,
                user_profile=user_profile,
                self_identity_profile=self_identity_profile,
                self_identity=self_identity_profile,
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
            message=prepared_message,
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
                "resolved_user_id": getattr(message, "resolved_user_id", None),
                "conversation_id": getattr(message, "conversation_id", None),
                "participant_display_name": getattr(message, "participant_display_name", None),
                "relationship_to_me": getattr(message, "relationship_to_me", None),
                "current_intent": getattr(message, "current_intent", None),
                "identity_confidence": getattr(message, "identity_confidence", None),
                "identity_status": getattr(message, "identity_status", None),
                "identity_evidence": getattr(message, "identity_evidence", []),
            }
        chat_type = str(values.get("chat_type", "friend")).strip() or "friend"
        if chat_type == "group":
            parsed = MessageParser.parse_group_message(
                chat_id=str(values.get("chat_id", "")),
                sender_name=str(values.get("sender_name", "")),
                text=str(values.get("text", "")),
                contexts=values.get("context"),
                timestamp=self._optional_text(values.get("timestamp")),
            )
        else:
            parsed = MessageParser.parse_friend_message(
                chat_id=str(values.get("chat_id", "")),
                text=str(values.get("text", "")),
                contexts=values.get("context"),
                sender_name=self._optional_text(values.get("sender_name")),
                timestamp=self._optional_text(values.get("timestamp")),
            )
        parsed.resolved_user_id = self._optional_text(values.get("resolved_user_id"))
        parsed.conversation_id = self._optional_text(values.get("conversation_id"))
        parsed.participant_display_name = self._optional_text(values.get("participant_display_name"))
        parsed.relationship_to_me = self._optional_text(values.get("relationship_to_me"))
        parsed.current_intent = self._optional_text(values.get("current_intent"))
        parsed.identity_status = self._optional_text(values.get("identity_status"))
        parsed.identity_confidence = self._optional_float(values.get("identity_confidence"))
        parsed.identity_evidence = self._string_list(values.get("identity_evidence"))
        return parsed

    def _load_user_profile(self, message: Message):
        if self.profile_store is None:
            return None
        user_id = message.resolved_user_id or (
            message.chat_id if message.chat_type == "friend" else message.sender_name or message.chat_id
        )
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

    def _load_self_identity_profile(self, *, message: Message, user_profile, agent_profile):
        resolver = self.self_identity_resolver
        if resolver is None:
            return None
        user_id = message.resolved_user_id or (
            message.chat_id if message.chat_type == "friend" else message.sender_name or message.chat_id
        )
        if not user_id:
            return None
        try:
            resolved = resolver.resolve(
                user_id=user_id,
                user_profile=user_profile,
                message=message,
                agent_profile=agent_profile,
                relationship_to_me=message.relationship_to_me,
            )
        except TypeError:
            try:
                resolved = resolver.resolve(
                    message=message,
                    user_profile=user_profile,
                    agent_profile=agent_profile,
                )
            except Exception:
                return None
        except Exception:
            return None
        self._log_event(
            "self_identity_resolved",
            user_id=user_id,
            relationship=getattr(resolved, "relationship", ""),
        )
        return resolved

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
        if self.memory_store is None:
            return None
        summaries = [
            self._load_memory_summary_for_target(
                target_id=chat_id.resolved_user_id,
                method_names=("load_user_summary_text", "load_user_memory_summary"),
            ),
            self._load_memory_summary_for_target(
                target_id=chat_id.conversation_id,
                method_names=("load_conversation_summary_text", "load_conversation_memory_summary"),
            ),
        ]
        combined = [summary for summary in summaries if summary]
        if combined:
            return "\n\n".join(combined)
        legacy_chat_id = chat_id.chat_id.strip()
        if not legacy_chat_id:
            return None
        loader = self._get_memory_store_method("load_summary_text")
        if loader is None:
            return None
        summary = loader(legacy_chat_id)
        cleaned = str(summary or "").strip()
        return cleaned or None

    def _append_memory_snapshot(
        self,
        *,
        message: Message,
        contexts: list[str],
        latest_message: str,
        reply: str,
    ) -> None:
        if self.memory_store is None:
            return
        snapshot_messages = [*contexts, latest_message, reply]
        appended = False
        appended = self._append_memory_snapshot_for_target(
            target_id=message.resolved_user_id,
            method_names=("append_user_snapshot", "append_user_memory_snapshot"),
            messages=snapshot_messages,
        ) or appended
        appended = self._append_memory_snapshot_for_target(
            target_id=message.conversation_id,
            method_names=("append_conversation_snapshot", "append_conversation_memory_snapshot"),
            messages=snapshot_messages,
        ) or appended
        if appended:
            return
        legacy_chat_id = message.chat_id.strip()
        if not legacy_chat_id:
            return
        appender = self._get_memory_store_method("append_snapshot")
        if appender is None:
            return
        appender(legacy_chat_id, snapshot_messages)

    def _build_prompt_preview(
        self,
        *,
        prepared_message: Message,
        agent_profile,
        user_profile,
        self_identity_profile,
        knowledge_chunks: list[str],
        memory_summary: str | None,
    ) -> str:
        return self._engine.prompt_builder.debug_preview(
            scene=prepared_message.chat_type,
            latest_message=prepared_message.text,
            contexts=prepared_message.context,
            agent_profile=agent_profile,
            user_profile=user_profile,
            self_identity_profile=self_identity_profile,
            self_identity=self_identity_profile,
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

    def _optional_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def _merge_message_metadata(self, source: Message, prepared: Message) -> Message:
        prepared.resolved_user_id = prepared.resolved_user_id or source.resolved_user_id
        prepared.conversation_id = prepared.conversation_id or source.conversation_id
        prepared.participant_display_name = prepared.participant_display_name or source.participant_display_name
        prepared.relationship_to_me = prepared.relationship_to_me or source.relationship_to_me
        prepared.current_intent = prepared.current_intent or source.current_intent
        prepared.identity_status = prepared.identity_status or source.identity_status
        prepared.identity_confidence = (
            prepared.identity_confidence
            if prepared.identity_confidence is not None
            else source.identity_confidence
        )
        if not prepared.identity_evidence:
            prepared.identity_evidence = list(source.identity_evidence)
        return prepared

    def _load_memory_summary_for_target(
        self,
        *,
        target_id: str | None,
        method_names: tuple[str, ...],
    ) -> str | None:
        if not target_id:
            return None
        cleaned_target_id = target_id.strip()
        if not cleaned_target_id:
            return None
        for method_name in method_names:
            loader = self._get_memory_store_method(method_name)
            if loader is None:
                continue
            summary = loader(cleaned_target_id)
            cleaned = str(summary or "").strip()
            if cleaned:
                return cleaned
        return None

    def _append_memory_snapshot_for_target(
        self,
        *,
        target_id: str | None,
        method_names: tuple[str, ...],
        messages: list[str],
    ) -> bool:
        if not target_id:
            return False
        cleaned_target_id = target_id.strip()
        if not cleaned_target_id:
            return False
        for method_name in method_names:
            appender = self._get_memory_store_method(method_name)
            if appender is None:
                continue
            appender(cleaned_target_id, messages)
            return True
        return False

    def _get_memory_store_method(self, method_name: str):
        method = getattr(self.memory_store, method_name, None)
        if callable(method):
            return method
        return None
