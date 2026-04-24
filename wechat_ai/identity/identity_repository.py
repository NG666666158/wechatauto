from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, TypeVar

from ..paths import DATA_DIR
from .identity_models import DraftUser, IdentityCandidate, UserAlias, UserIdentity


T = TypeVar("T")


class IdentityRepository:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else DATA_DIR / "identity"

    def load_users(self) -> list[UserIdentity]:
        return self._load_list("users.json", UserIdentity)

    def save_users(self, users: list[UserIdentity]) -> None:
        self._save_list("users.json", users)

    def load_aliases(self) -> list[UserAlias]:
        return self._load_list("user_aliases.json", UserAlias)

    def save_aliases(self, aliases: list[UserAlias]) -> None:
        self._save_list("user_aliases.json", aliases)

    def load_draft_users(self) -> list[DraftUser]:
        return self._load_list("draft_users.json", DraftUser)

    def save_draft_users(self, drafts: list[DraftUser]) -> None:
        self._save_list("draft_users.json", drafts)

    def load_candidates(self) -> list[IdentityCandidate]:
        return self._load_list("identity_candidates.json", IdentityCandidate)

    def save_candidates(self, candidates: list[IdentityCandidate]) -> None:
        self._save_list("identity_candidates.json", candidates)

    def _load_list(self, filename: str, model_type: type[T]) -> list[T]:
        path = self.base_dir / filename
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            return []
        field_names = {field.name for field in fields(model_type)}
        return [
            model_type(**{key: value for key, value in item.items() if key in field_names})
            for item in payload
            if isinstance(item, dict)
        ]

    def _save_list(self, filename: str, items: list[Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = [asdict(item) for item in items]
        with (self.base_dir / filename).open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
