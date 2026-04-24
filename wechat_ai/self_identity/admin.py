from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from wechat_ai.profile.user_profile import UserProfile

from .models import GlobalSelfIdentityProfile, RelationshipSelfIdentityProfile, UserSelfIdentityOverride
from .resolver import SelfIdentityResolver
from .store import SelfIdentityStore


def _store(base_dir: Path | None = None) -> SelfIdentityStore:
    return SelfIdentityStore(base_dir=base_dir)


def load_global_profile(*, base_dir: Path | None = None) -> dict[str, Any]:
    return asdict(_store(base_dir).load_global_profile())


def update_global_profile(patch: Mapping[str, object], *, base_dir: Path | None = None) -> dict[str, Any]:
    store = _store(base_dir)
    current = asdict(store.load_global_profile())
    merged = {**current, **dict(patch)}
    saved = store.save_global_profile(GlobalSelfIdentityProfile(**merged))
    return asdict(saved)


def list_relationship_profiles(*, base_dir: Path | None = None) -> list[dict[str, Any]]:
    return [asdict(profile) for profile in _store(base_dir).list_relationship_profiles()]


def load_relationship_profile(relationship: str, *, base_dir: Path | None = None) -> dict[str, Any]:
    return asdict(_store(base_dir).load_relationship_profile(relationship))


def update_relationship_profile(
    relationship: str,
    patch: Mapping[str, object],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    store = _store(base_dir)
    current = asdict(store.load_relationship_profile(relationship))
    merged = {**current, **dict(patch), "relationship": relationship}
    saved = store.save_relationship_profile(RelationshipSelfIdentityProfile(**merged))
    return asdict(saved)


def list_user_overrides(*, base_dir: Path | None = None) -> list[dict[str, Any]]:
    return [asdict(item) for item in _store(base_dir).list_user_overrides()]


def load_user_override(user_id: str, *, base_dir: Path | None = None) -> dict[str, Any]:
    return asdict(_store(base_dir).load_user_override(user_id))


def update_user_override(
    user_id: str,
    patch: Mapping[str, object],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    store = _store(base_dir)
    current = asdict(store.load_user_override(user_id))
    merged = {**current, **dict(patch), "user_id": user_id}
    saved = store.save_user_override(UserSelfIdentityOverride(**merged))
    return asdict(saved)


def preview_resolved_profile(
    user_id: str,
    *,
    tags: list[str] | None = None,
    display_name: str = "",
    relationship_to_me: str | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    resolver = SelfIdentityResolver(_store(base_dir))
    profile = UserProfile(user_id=user_id, display_name=display_name, tags=list(tags or []))
    resolved = resolver.resolve(
        user_id=user_id,
        user_profile=profile,
        relationship_to_me=relationship_to_me,
    )
    return asdict(resolved)

