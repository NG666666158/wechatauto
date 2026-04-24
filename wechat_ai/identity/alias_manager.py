from __future__ import annotations

from .identity_models import UserAlias
from .identity_repository import IdentityRepository


class AliasManager:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def resolve_alias(self, *, display_name: str, group_name: str | None = None) -> str | None:
        name = self._normalize(display_name)
        group = self._normalize(group_name)
        if not name:
            return None
        for alias in self.repository.load_aliases():
            if name in {self._normalize(item) for item in alias.display_names}:
                return alias.user_id
            if name in {self._normalize(item) for item in alias.remarks}:
                return alias.user_id
            for group_nickname in alias.group_nicknames:
                nickname_group = self._normalize(group_nickname.get("group_name"))
                nickname_name = self._normalize(group_nickname.get("name"))
                if name == nickname_name and (not group or group == nickname_group):
                    return alias.user_id
        return None

    def add_alias(
        self,
        *,
        user_id: str,
        display_name: str,
        group_name: str | None = None,
        updated_at: str = "",
    ) -> None:
        aliases = self.repository.load_aliases()
        alias = next((item for item in aliases if item.user_id == user_id), None)
        if alias is None:
            alias = UserAlias(user_id=user_id)
            aliases.append(alias)
        clean_name = display_name.strip()
        if group_name:
            entry = {"group_name": group_name.strip(), "name": clean_name}
            if entry not in alias.group_nicknames:
                alias.group_nicknames.append(entry)
        elif clean_name and clean_name not in alias.display_names:
            alias.display_names.append(clean_name)
        alias.latest_seen_name = clean_name or alias.latest_seen_name
        alias.updated_at = updated_at or alias.updated_at
        self.repository.save_aliases(aliases)

    def _normalize(self, value: str | None) -> str:
        return str(value or "").strip().casefold()
