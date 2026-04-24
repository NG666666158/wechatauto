from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .identity_models import IdentityRawSignal, UserAlias, UserIdentity


@dataclass(slots=True)
class IdentityMatch:
    matched_user_id: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


class IdentityMatcher:
    def match(
        self,
        *,
        signal: IdentityRawSignal,
        users: list[UserIdentity],
        aliases: list[UserAlias],
    ) -> IdentityMatch | None:
        best_match: IdentityMatch | None = None
        alias_by_user_id = {alias.user_id: alias for alias in aliases}
        for user in users:
            alias = alias_by_user_id.get(user.user_id)
            candidate_names = self._candidate_names(user, alias, signal.group_name)
            if not candidate_names:
                candidate_names = [user.canonical_name]
            alias_similarity = self._alias_similarity(signal.sender_name or signal.display_name, candidate_names)
            same_group_context = self._same_group_context(signal.group_name, alias)
            keyword_overlap = self._keyword_overlap(signal, candidate_names)
            recent_context_continuity = self._recent_context_continuity(signal, candidate_names)
            confidence = min(
                1.0,
                (alias_similarity * 0.65)
                + (same_group_context * 0.15)
                + (keyword_overlap * 0.10)
                + (recent_context_continuity * 0.10),
            )
            evidence: list[str] = []
            if alias_similarity >= 0.20:
                evidence.append("alias_similarity")
            if same_group_context > 0:
                evidence.append("same_group_context")
            if keyword_overlap > 0:
                evidence.append("keyword_overlap")
            if recent_context_continuity > 0:
                evidence.append("recent_context_continuity")
            current_match = IdentityMatch(
                matched_user_id=user.user_id,
                confidence=round(confidence, 4),
                evidence=evidence,
            )
            if best_match is None or current_match.confidence > best_match.confidence:
                best_match = current_match
        return best_match

    def _candidate_names(
        self,
        user: UserIdentity,
        alias: UserAlias | None,
        group_name: str | None,
    ) -> list[str]:
        names = [user.canonical_name]
        if alias is None:
            return [name for name in names if name]
        names.extend(alias.display_names)
        names.extend(alias.remarks)
        if alias.latest_seen_name:
            names.append(alias.latest_seen_name)
        for group_nickname in alias.group_nicknames:
            nickname = str(group_nickname.get("name") or "").strip()
            if not nickname:
                continue
            names.append(nickname)
            if group_name and self._normalize(group_nickname.get("group_name")) == self._normalize(group_name):
                names.append(nickname)
        return [name for name in names if str(name).strip()]

    def _alias_similarity(self, incoming_name: str | None, candidate_names: list[str]) -> float:
        incoming = self._normalize(incoming_name)
        if not incoming:
            return 0.0
        best = 0.0
        for candidate_name in candidate_names:
            candidate = self._normalize(candidate_name)
            if not candidate:
                continue
            score = SequenceMatcher(a=incoming, b=candidate).ratio()
            if len(incoming) >= 3 and len(candidate) >= 3 and (incoming in candidate or candidate in incoming):
                score = max(score, min(len(incoming), len(candidate)) / max(len(incoming), len(candidate)))
            best = max(best, score)
        return best

    def _same_group_context(self, group_name: str | None, alias: UserAlias | None) -> float:
        if alias is None or not group_name:
            return 0.0
        target_group = self._normalize(group_name)
        for item in alias.group_nicknames:
            if self._normalize(item.get("group_name")) == target_group:
                return 1.0
        return 0.0

    def _keyword_overlap(self, signal: IdentityRawSignal, candidate_names: list[str]) -> float:
        signal_keywords = self._keywords(
            " ".join(
                [signal.display_name, signal.sender_name or "", signal.text, *signal.contexts]
            )
        )
        candidate_keywords = self._keywords(" ".join(candidate_names))
        if not signal_keywords or not candidate_keywords:
            return 0.0
        overlap = signal_keywords & candidate_keywords
        if not overlap:
            return 0.0
        return len(overlap) / len(candidate_keywords)

    def _recent_context_continuity(self, signal: IdentityRawSignal, candidate_names: list[str]) -> float:
        contexts = [str(context or "").casefold() for context in signal.contexts if str(context or "").strip()]
        if not contexts:
            return 0.0
        candidate_keywords = self._keywords(" ".join(candidate_names))
        if any(keyword in context for context in contexts for keyword in candidate_keywords if len(keyword) >= 3):
            return 1.0
        for candidate_name in candidate_names:
            normalized_name = self._normalize(candidate_name)
            if len(normalized_name) >= 4 and any(normalized_name in self._normalize(context) for context in contexts):
                return 1.0
        return 0.0

    def _keywords(self, value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", str(value or "").casefold())
            if len(token) >= 2
        }

    def _normalize(self, value: str | None) -> str:
        text = str(value or "").strip().casefold()
        return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)
