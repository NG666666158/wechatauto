from __future__ import annotations

from typing import Iterable

from wechat_ai.models import Message


class MessageParser:
    """Normalize runtime message inputs into shared Message objects."""

    @staticmethod
    def parse_friend_message(
        chat_id: str,
        text: str,
        contexts: Iterable[str] | None = None,
        *,
        sender_name: str | None = None,
        timestamp: str | None = None,
    ) -> Message:
        normalized_chat_id = MessageParser._normalize_text(chat_id)
        return Message(
            chat_id=normalized_chat_id,
            chat_type="friend",
            sender_name=MessageParser._normalize_text(sender_name) or normalized_chat_id,
            text=MessageParser._normalize_text(text),
            timestamp=timestamp,
            context=MessageParser._normalize_contexts(contexts),
        )

    @staticmethod
    def parse_group_message(
        chat_id: str,
        sender_name: str,
        text: str,
        contexts: Iterable[str] | None = None,
        *,
        timestamp: str | None = None,
    ) -> Message:
        normalized_chat_id = MessageParser._normalize_text(chat_id)
        return Message(
            chat_id=normalized_chat_id,
            chat_type="group",
            sender_name=MessageParser._normalize_text(sender_name) or normalized_chat_id,
            text=MessageParser._normalize_text(text),
            timestamp=timestamp,
            context=MessageParser._normalize_contexts(contexts),
        )

    @staticmethod
    def _normalize_contexts(contexts: Iterable[str] | None) -> list[str]:
        if contexts is None:
            return []
        normalized: list[str] = []
        for item in contexts:
            cleaned = MessageParser._normalize_text(item)
            if cleaned:
                normalized.append(cleaned)
        return normalized

    @staticmethod
    def _normalize_text(value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()
