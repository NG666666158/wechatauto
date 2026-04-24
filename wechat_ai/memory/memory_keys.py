from __future__ import annotations


def _normalize_memory_part(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_user_memory_key(resolved_user_id: str) -> str:
    normalized = _normalize_memory_part(resolved_user_id)
    if normalized is None:
        raise ValueError("resolved_user_id is required")
    return f"user:{normalized}"


def build_conversation_memory_key(conversation_id: str) -> str:
    normalized = _normalize_memory_part(conversation_id)
    if normalized is None:
        raise ValueError("conversation_id is required")
    return f"conversation:{normalized}"


def build_memory_lookup_keys(
    *,
    resolved_user_id: str | None = None,
    conversation_id: str | None = None,
    chat_id: str | None = None,
) -> list[str]:
    keys: list[str] = []
    normalized_user_id = _normalize_memory_part(resolved_user_id)
    normalized_conversation_id = _normalize_memory_part(conversation_id)
    normalized_chat_id = _normalize_memory_part(chat_id)

    if normalized_user_id is not None:
        keys.append(build_user_memory_key(normalized_user_id))
    if normalized_conversation_id is not None:
        keys.append(build_conversation_memory_key(normalized_conversation_id))
    if normalized_chat_id is not None and normalized_chat_id not in keys:
        keys.append(normalized_chat_id)
    return keys


def choose_primary_memory_key(
    *,
    resolved_user_id: str | None = None,
    conversation_id: str | None = None,
    chat_id: str | None = None,
) -> str:
    keys = build_memory_lookup_keys(
        resolved_user_id=resolved_user_id,
        conversation_id=conversation_id,
        chat_id=chat_id,
    )
    if not keys:
        raise ValueError("at least one identity value is required")
    return keys[0]
