from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from wechat_ai.storage_names import safe_storage_name

from .models import (
    GlobalSelfIdentityProfile,
    RelationshipSelfIdentityProfile,
    UserSelfIdentityOverride,
)


class SelfIdentityStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        root = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[1] / "data" / "self_identity"
        self.base_dir = root
        self.relationship_profiles_dir = root / "relationship_profiles"
        self.user_overrides_dir = root / "user_overrides"
        self.global_profile_path = root / "global_profile.json"

    def load_global_profile(self) -> GlobalSelfIdentityProfile:
        payload = self._read_json(self.global_profile_path, asdict(GlobalSelfIdentityProfile()))
        return GlobalSelfIdentityProfile(**self._normalize_global_payload(payload))

    def save_global_profile(self, profile: GlobalSelfIdentityProfile) -> GlobalSelfIdentityProfile:
        normalized = GlobalSelfIdentityProfile(**self._normalize_global_payload(asdict(profile)))
        self._write_json(self.global_profile_path, asdict(normalized))
        return normalized

    def load_relationship_profile(self, relationship: str) -> RelationshipSelfIdentityProfile:
        normalized_relationship = self._normalize_key(relationship, fallback="general")
        default = asdict(RelationshipSelfIdentityProfile(relationship=normalized_relationship))
        payload = self._read_json(self._relationship_profile_path(normalized_relationship), default)
        payload["relationship"] = normalized_relationship
        return RelationshipSelfIdentityProfile(**self._normalize_relationship_payload(payload))

    def save_relationship_profile(
        self,
        profile: RelationshipSelfIdentityProfile,
    ) -> RelationshipSelfIdentityProfile:
        normalized = RelationshipSelfIdentityProfile(**self._normalize_relationship_payload(asdict(profile)))
        self._write_json(self._relationship_profile_path(normalized.relationship), asdict(normalized))
        return normalized

    def list_relationship_profiles(self) -> list[RelationshipSelfIdentityProfile]:
        if not self.relationship_profiles_dir.exists():
            return []
        profiles: list[RelationshipSelfIdentityProfile] = []
        for path in sorted(self.relationship_profiles_dir.glob("*.json")):
            profiles.append(self.load_relationship_profile(path.stem))
        return profiles

    def load_user_override(self, user_id: str) -> UserSelfIdentityOverride:
        default = asdict(UserSelfIdentityOverride(user_id=user_id))
        payload = self._read_json(self._user_override_path(user_id), default)
        payload["user_id"] = user_id
        return UserSelfIdentityOverride(**self._normalize_user_override_payload(payload))

    def save_user_override(self, override: UserSelfIdentityOverride) -> UserSelfIdentityOverride:
        normalized = UserSelfIdentityOverride(**self._normalize_user_override_payload(asdict(override)))
        self._write_json(self._user_override_path(normalized.user_id), asdict(normalized))
        return normalized

    def list_user_overrides(self) -> list[UserSelfIdentityOverride]:
        if not self.user_overrides_dir.exists():
            return []
        overrides: list[UserSelfIdentityOverride] = []
        for path in sorted(self.user_overrides_dir.glob("*.json")):
            payload = self._read_json(path, {})
            user_id = str(payload.get("user_id", "")).strip() or path.stem
            payload["user_id"] = user_id
            overrides.append(UserSelfIdentityOverride(**self._normalize_user_override_payload(payload)))
        return overrides

    def _read_json(self, path: Path, default: dict[str, object]) -> dict[str, object]:
        if not path.exists():
            return dict(default)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else dict(default)

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _relationship_profile_path(self, relationship: str) -> Path:
        safe_name = safe_storage_name(relationship, fallback="general")
        return self.relationship_profiles_dir / f"{safe_name}.json"

    def _user_override_path(self, user_id: str) -> Path:
        safe_name = safe_storage_name(user_id, fallback="unknown_user")
        return self.user_overrides_dir / f"{safe_name}.json"

    def _normalize_global_payload(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "profile_id": "global",
            "display_name": self._normalize_text(payload.get("display_name")),
            "identity_facts": self._normalize_list(payload.get("identity_facts")),
            "constraints": self._normalize_list(payload.get("constraints")),
            "style_hints": self._normalize_list(payload.get("style_hints")),
            "notes": self._normalize_list(payload.get("notes")),
        }

    def _normalize_relationship_payload(self, payload: dict[str, object]) -> dict[str, object]:
        relationship = self._normalize_key(payload.get("relationship"), fallback="general")
        return {
            "relationship": relationship,
            "display_name": self._normalize_text(payload.get("display_name")),
            "trigger_tags": self._normalize_list(payload.get("trigger_tags")),
            "identity_facts": self._normalize_list(payload.get("identity_facts")),
            "constraints": self._normalize_list(payload.get("constraints")),
            "style_hints": self._normalize_list(payload.get("style_hints")),
            "notes": self._normalize_list(payload.get("notes")),
        }

    def _normalize_user_override_payload(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "user_id": self._normalize_text(payload.get("user_id")),
            "relationship_override": self._normalize_key(payload.get("relationship_override"), fallback=""),
            "display_name": self._normalize_text(payload.get("display_name")),
            "identity_facts": self._normalize_list(payload.get("identity_facts")),
            "constraints": self._normalize_list(payload.get("constraints")),
            "style_hints": self._normalize_list(payload.get("style_hints")),
            "notes": self._normalize_list(payload.get("notes")),
        }

    def _normalize_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned

    def _normalize_text(self, value: object) -> str:
        return str(value or "").strip()

    def _normalize_key(self, value: object, *, fallback: str) -> str:
        text = self._normalize_text(value).lower().replace(" ", "_")
        return text or fallback

