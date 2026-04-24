from __future__ import annotations

from uuid import uuid4

from .alias_manager import AliasManager
from .identity_bootstrapper import IdentityBootstrapper
from .identity_matcher import IdentityMatcher
from .identity_models import DraftUser, IdentityCandidate, IdentityRawSignal, IdentityResolutionResult
from .identity_repository import IdentityRepository


class IdentityResolver:
    def __init__(
        self,
        *,
        repository: IdentityRepository | None = None,
        alias_manager: AliasManager | None = None,
        bootstrapper: IdentityBootstrapper | None = None,
        matcher: IdentityMatcher | None = None,
        event_logger=None,
    ) -> None:
        self.repository = repository or IdentityRepository()
        self.alias_manager = alias_manager or AliasManager(self.repository)
        self.bootstrapper = bootstrapper or IdentityBootstrapper()
        self.matcher = matcher or IdentityMatcher()
        self.event_logger = event_logger

    def resolve(self, signal: IdentityRawSignal) -> IdentityResolutionResult:
        self._log_event(
            "identity_resolve_started",
            conversation_id=signal.conversation_id,
            chat_type=signal.chat_type,
            display_name=signal.display_name,
            group_name=signal.group_name,
        )
        user_id = self.alias_manager.resolve_alias(
            display_name=signal.sender_name or signal.display_name,
            group_name=signal.group_name,
        )
        if user_id:
            self._log_event(
                "identity_alias_hit",
                conversation_id=signal.conversation_id,
                resolved_user_id=user_id,
                evidence=["alias_exact_match"],
            )
            return IdentityResolutionResult(
                resolved_user_id=user_id,
                conversation_id=signal.conversation_id,
                participant_display_name=signal.sender_name or signal.display_name,
                identity_confidence=0.99,
                identity_status="resolved",
                evidence=["alias_exact_match"],
            )

        match = self.matcher.match(
            signal=signal,
            users=self.repository.load_users(),
            aliases=self.repository.load_aliases(),
        )
        participant_name = signal.sender_name or signal.display_name
        if match is not None and match.confidence >= 0.85:
            self.alias_manager.add_alias(
                user_id=match.matched_user_id,
                display_name=participant_name,
                group_name=signal.group_name,
                updated_at=signal.captured_at or "",
            )
            self._log_event(
                "identity_auto_merged",
                conversation_id=signal.conversation_id,
                resolved_user_id=match.matched_user_id,
                confidence=match.confidence,
                evidence=match.evidence,
            )
            self._log_event(
                "identity_alias_updated",
                conversation_id=signal.conversation_id,
                resolved_user_id=match.matched_user_id,
                alias=participant_name,
                group_name=signal.group_name,
            )
            return IdentityResolutionResult(
                resolved_user_id=match.matched_user_id,
                conversation_id=signal.conversation_id,
                participant_display_name=participant_name,
                identity_confidence=match.confidence,
                identity_status="resolved",
                evidence=list(match.evidence),
            )

        if match is not None and match.confidence >= 0.60:
            candidate = self._upsert_candidate(signal, match)
            self._log_event(
                "identity_candidate_generated",
                conversation_id=signal.conversation_id,
                candidate_id=candidate.candidate_id,
                matched_user_id=candidate.matched_user_id,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
            )
            self._log_event(
                "identity_review_required",
                conversation_id=signal.conversation_id,
                candidate_id=candidate.candidate_id,
                matched_user_id=candidate.matched_user_id,
                confidence=candidate.confidence,
            )
            return IdentityResolutionResult(
                candidate_id=candidate.candidate_id,
                conversation_id=signal.conversation_id,
                participant_display_name=participant_name,
                identity_confidence=candidate.confidence,
                identity_status="review",
                evidence=list(candidate.evidence),
            )

        draft = self._find_existing_draft(signal)
        created = False
        if draft is None:
            draft = self.bootstrapper.create_draft(signal)
            drafts = self.repository.load_draft_users()
            drafts.append(draft)
            self.repository.save_draft_users(drafts)
            created = True
        if created:
            self._log_event(
                "identity_draft_created",
                conversation_id=signal.conversation_id,
                draft_user_id=draft.draft_user_id,
                confidence=draft.confidence,
                source_signals=draft.source_signals,
            )
        return IdentityResolutionResult(
            draft_user_id=draft.draft_user_id,
            conversation_id=signal.conversation_id,
            participant_display_name=signal.sender_name or signal.display_name,
            relationship_to_me=draft.relationship_to_me,
            current_intent=draft.current_intent,
            identity_confidence=draft.confidence,
            identity_status="draft",
            evidence=list(draft.source_signals),
        )

    def _upsert_candidate(self, signal: IdentityRawSignal, match) -> IdentityCandidate:
        candidates = self.repository.load_candidates()
        incoming_name = (signal.sender_name or signal.display_name).strip()
        for candidate in candidates:
            if (
                candidate.conversation_id == signal.conversation_id
                and candidate.incoming_name == incoming_name
                and candidate.matched_user_id == match.matched_user_id
                and candidate.status == "pending_review"
            ):
                candidate.confidence = match.confidence
                candidate.evidence = list(match.evidence)
                candidate.updated_at = signal.captured_at or candidate.updated_at
                self.repository.save_candidates(candidates)
                return candidate
        candidate = IdentityCandidate(
            candidate_id=f"candidate_{uuid4().hex[:12]}",
            conversation_id=signal.conversation_id,
            incoming_name=incoming_name,
            matched_user_id=match.matched_user_id,
            confidence=match.confidence,
            evidence=list(match.evidence),
            created_at=signal.captured_at or "",
            updated_at=signal.captured_at or "",
        )
        candidates.append(candidate)
        self.repository.save_candidates(candidates)
        return candidate

    def _find_existing_draft(self, signal: IdentityRawSignal) -> DraftUser | None:
        for draft in self.repository.load_draft_users():
            if draft.conversation_id == signal.conversation_id and draft.status == "draft":
                return draft
        return None

    def _log_event(self, event_type: str, **fields: object) -> None:
        if self.event_logger is None:
            return
        self.event_logger.log_event(event_type, **fields)
