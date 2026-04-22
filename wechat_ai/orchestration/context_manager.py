from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from wechat_ai.models import Message


class ContextManager:
    """Owns recent-context trimming so future summary behavior can live here."""

    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages

    def prepare_message(self, message: Message) -> Message:
        return replace(message, context=self.build_context_window(message.context))

    def build_context_window(self, contexts: Iterable[str]) -> list[str]:
        cleaned = [str(item).strip() for item in contexts if str(item).strip()]
        if self.max_messages <= 0:
            return cleaned
        return cleaned[-self.max_messages :]
