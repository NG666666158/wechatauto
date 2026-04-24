from __future__ import annotations

import re
from hashlib import sha1


_WINDOWS_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_WHITESPACE = re.compile(r"\s+")
_MAX_STORAGE_NAME_LENGTH = 120
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def safe_storage_name(identifier: str, *, fallback: str) -> str:
    value = str(identifier).strip()
    value = _WINDOWS_INVALID_CHARS.sub("_", value)
    value = _WHITESPACE.sub("_", value)
    value = value.strip("._ ")
    if not value:
        return fallback
    if value.upper() in _RESERVED_WINDOWS_NAMES:
        value = f"{value}_"
    if len(value) > _MAX_STORAGE_NAME_LENGTH:
        digest = sha1(str(identifier).encode("utf-8")).hexdigest()[:10]
        value = f"{value[: _MAX_STORAGE_NAME_LENGTH - 11].rstrip('._ ')}_{digest}"
    return value
