from __future__ import annotations

from wechat_ai.identity.identity_models import IdentityResolutionResult

from .models import (
    GlobalSelfIdentityProfile,
    RelationshipSelfIdentityProfile,
    ResolvedSelfIdentityProfile,
    UserSelfIdentityOverride,
)
from .store import SelfIdentityStore


class SelfIdentityResolver:
    def __init__(self, store: SelfIdentityStore | None = None) -> None:
        self.store = store or SelfIdentityStore()

    def resolve(
        self,
        *,
        user_id: str,
        user_profile=None,
        message=None,
        agent_profile=None,
        relationship_to_me: str | None = None,
        identity_result: IdentityResolutionResult | None = None,
    ) -> ResolvedSelfIdentityProfile:
        del agent_profile
        if relationship_to_me is None and message is not None:
            relationship_to_me = getattr(message, "relationship_to_me", None)
        global_profile = self.store.load_global_profile()
        user_override = self.store.load_user_override(user_id)
        relationship = self._resolve_relationship(
            user_profile=user_profile,
            relationship_to_me=relationship_to_me,
            identity_result=identity_result,
            user_override=user_override,
        )
        relationship_profile = self.store.load_relationship_profile(relationship) if relationship else None
        resolved = ResolvedSelfIdentityProfile(
            user_id=user_id,
            relationship=relationship,
            display_name=self._first_text(
                user_override.display_name,
                getattr(user_profile, "display_name", ""),
                relationship_profile.display_name if relationship_profile else "",
                global_profile.display_name,
            ),
            identity_facts=self._merge_lists(
                global_profile.identity_facts,
                relationship_profile.identity_facts if relationship_profile else [],
                user_override.identity_facts,
            ),
            constraints=self._merge_lists(
                global_profile.constraints,
                relationship_profile.constraints if relationship_profile else [],
                user_override.constraints,
            ),
            style_hints=self._merge_lists(
                global_profile.style_hints,
                relationship_profile.style_hints if relationship_profile else [],
                user_override.style_hints,
            ),
            notes=self._merge_lists(
                global_profile.notes,
                relationship_profile.notes if relationship_profile else [],
                user_override.notes,
            ),
            sources=self._build_sources(
                global_profile=global_profile,
                relationship_profile=relationship_profile,
                user_override=user_override,
            ),
        )
        resolved.summary = self.render_summary(resolved)
        return resolved

    def render_summary(self, profile: ResolvedSelfIdentityProfile | None) -> str:
        if profile is None:
            return ""
        lines: list[str] = []
        if profile.display_name:
            lines.append(f"称呼: {profile.display_name}")
        if profile.relationship:
            lines.append(f"关系场景: {profile.relationship}")
        lines.extend(f"事实: {item}" for item in profile.identity_facts)
        lines.extend(f"约束: {item}" for item in profile.constraints)
        lines.extend(f"风格: {item}" for item in profile.style_hints)
        lines.extend(f"备注: {item}" for item in profile.notes)
        return "\n".join(lines)

    def _resolve_relationship(
        self,
        *,
        user_profile,
        relationship_to_me: str | None,
        identity_result: IdentityResolutionResult | None,
        user_override: UserSelfIdentityOverride,
    ) -> str:
        override_value = self._normalize_relationship(user_override.relationship_override)
        if override_value:
            return override_value
        tags = getattr(user_profile, "tags", []) if user_profile is not None else []
        tag_match = self._relationship_from_tags(tags)
        if tag_match:
            return tag_match
        explicit = self._normalize_relationship(relationship_to_me)
        if explicit:
            return explicit
        if identity_result is not None:
            identity_value = self._normalize_relationship(identity_result.relationship_to_me)
            if identity_value:
                return identity_value
        return ""

    def _relationship_from_tags(self, tags: object) -> str:
        if not isinstance(tags, list):
            return ""
        for raw in tags:
            normalized = self._normalize_relationship(raw)
            if normalized:
                return normalized
        return ""

    def _normalize_relationship(self, value: object) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        mapping = {
            "老师": "teacher",
            "teacher": "teacher",
            "父母": "parent",
            "家人": "parent",
            "爸爸": "parent",
            "妈妈": "parent",
            "parent": "parent",
            "朋友": "friend",
            "friend": "friend",
            "客户": "customer",
            "意向客户": "customer",
            "customer": "customer",
            "同事": "colleague",
            "colleague": "colleague",
        }
        return mapping.get(text, text.replace(" ", "_"))

    def _merge_lists(self, *parts: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for part in parts:
            for item in part:
                text = str(item).strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                merged.append(text)
        return merged

    def _build_sources(
        self,
        *,
        global_profile: GlobalSelfIdentityProfile,
        relationship_profile: RelationshipSelfIdentityProfile | None,
        user_override: UserSelfIdentityOverride,
    ) -> list[str]:
        sources = ["global_profile"]
        if relationship_profile is not None:
            sources.append(f"relationship:{relationship_profile.relationship}")
        if any(
            [
                user_override.relationship_override,
                user_override.display_name,
                user_override.identity_facts,
                user_override.constraints,
                user_override.style_hints,
                user_override.notes,
            ]
        ):
            sources.append(f"user_override:{user_override.user_id}")
        return sources

    def _first_text(self, *values: object) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""
