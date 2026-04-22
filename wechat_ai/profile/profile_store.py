from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

from ..paths import AGENTS_DIR, USERS_DIR
from .tag_manager import TagManager


@dataclass(slots=True)
class _FallbackUserProfile:
    user_id: str
    tags: list[str]
    notes: list[str] | None = None
    preferences: dict[str, str] | dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []
        if self.preferences is None:
            self.preferences = {}


@dataclass(slots=True)
class _FallbackAgentProfile:
    agent_id: str
    display_name: str = ""
    summary: str = ""
    tags: list[str] | None = None
    style_rules: list[str] | None = None
    goals: list[str] | None = None
    forbidden_rules: list[str] | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
        if self.style_rules is None:
            self.style_rules = []
        if self.goals is None:
            self.goals = []
        if self.forbidden_rules is None:
            self.forbidden_rules = []


class ProfileStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        root_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[1] / "data"
        self.base_dir = root_dir
        self.user_profiles_dir = self.base_dir / USERS_DIR.name
        self.agent_profiles_dir = self.base_dir / AGENTS_DIR.name

    def load_user_profile(self, user_id: str) -> Any:
        profile_type = self._load_user_profile_type()
        profile_path = self.user_profiles_dir / f"{user_id}.json"
        payload = self._read_or_create(profile_path, lambda: self._default_user_payload(profile_type, user_id))
        profile = self._build_profile(profile_type, payload, defaults=self._default_user_payload(profile_type, user_id))
        self.save_user_profile(profile)
        return profile

    def save_user_profile(self, profile: Any) -> None:
        profile_type = type(profile)
        payload = self._profile_to_payload(profile)
        payload["tags"] = TagManager.normalize(self._coerce_string_list(payload.get("tags")))
        user_id = str(payload.get("user_id") or getattr(profile, "user_id"))
        self._write_json(self.user_profiles_dir / f"{user_id}.json", payload)

    def load_agent_profile(self, agent_id: str) -> Any:
        profile_type = self._load_agent_profile_type()
        profile_path = self.agent_profiles_dir / f"{agent_id}.json"
        payload = self._read_or_create(profile_path, lambda: self._default_agent_payload(profile_type, agent_id))
        profile = self._build_profile(profile_type, payload, defaults=self._default_agent_payload(profile_type, agent_id))
        self.save_agent_profile(profile)
        return profile

    def save_agent_profile(self, profile: Any) -> None:
        payload = self._profile_to_payload(profile)
        payload["tags"] = TagManager.normalize(self._coerce_string_list(payload.get("tags")))
        for key in ("style_rules", "goals", "forbidden_rules"):
            payload[key] = self._coerce_string_list(payload.get(key))
        agent_id = str(payload.get("agent_id") or getattr(profile, "agent_id"))
        self._write_json(self.agent_profiles_dir / f"{agent_id}.json", payload)

    def _load_user_profile_type(self) -> type[Any]:
        try:
            from wechat_ai.profile.user_profile import UserProfile
        except ImportError:
            return _FallbackUserProfile
        return UserProfile

    def _load_agent_profile_type(self) -> type[Any]:
        try:
            from wechat_ai.profile.agent_profile import AgentProfile
        except ImportError:
            return _FallbackAgentProfile
        return AgentProfile

    def _read_or_create(self, path: Path, default_factory: Any) -> dict[str, Any]:
        if not path.exists():
            payload = default_factory()
            self._write_json(path, payload)
            return payload
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _build_profile(self, profile_type: type[Any], payload: dict[str, Any], defaults: dict[str, Any]) -> Any:
        field_names = {field.name for field in fields(profile_type)} if is_dataclass(profile_type) else set(defaults)
        merged = {**defaults, **payload}
        filtered = {key: value for key, value in merged.items() if key in field_names}
        if "tags" in filtered:
            filtered["tags"] = TagManager.normalize(self._coerce_string_list(filtered.get("tags")))
        for key in ("style_rules", "goals", "forbidden_rules"):
            if key in filtered:
                filtered[key] = self._coerce_string_list(filtered.get(key))
        return profile_type(**filtered)

    def _profile_to_payload(self, profile: Any) -> dict[str, Any]:
        if is_dataclass(profile):
            payload = asdict(profile)
        else:
            payload = dict(vars(profile))
        return {key: value for key, value in payload.items() if not key.startswith("_")}

    def _default_user_payload(self, profile_type: type[Any], user_id: str) -> dict[str, Any]:
        return self._defaults_for_profile_type(
            profile_type,
            {
                "user_id": user_id,
                "tags": [],
                "notes": [],
                "preferences": {},
            },
        )

    def _default_agent_payload(self, profile_type: type[Any], agent_id: str) -> dict[str, Any]:
        return self._defaults_for_profile_type(
            profile_type,
            {
                "agent_id": agent_id,
                "display_name": "",
                "summary": "",
                "tags": [],
                "style_rules": [],
                "goals": [],
                "forbidden_rules": [],
            },
        )

    def _defaults_for_profile_type(self, profile_type: type[Any], seed: dict[str, Any]) -> dict[str, Any]:
        if not is_dataclass(profile_type):
            return dict(seed)
        defaults: dict[str, Any] = {}
        for field in fields(profile_type):
            if field.name in seed:
                defaults[field.name] = seed[field.name]
        return defaults

    def _coerce_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]
