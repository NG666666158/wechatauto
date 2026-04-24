from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .alias_manager import AliasManager
from .identity_models import DraftUser, IdentityCandidate, UserIdentity
from .identity_repository import IdentityRepository


def list_users(*, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    return [asdict(user) for user in _repository(base_dir).load_users()]


def list_drafts(*, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    return [asdict(draft) for draft in _repository(base_dir).load_draft_users()]


def list_candidates(*, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    return [asdict(candidate) for candidate in _repository(base_dir).load_candidates()]


def confirm_draft(
    draft_id: str,
    *,
    user_id: str | None = None,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    repo = _repository(base_dir)
    drafts = repo.load_draft_users()
    draft = _find_by_id(drafts, "draft_user_id", draft_id)
    users = repo.load_users()
    alias_manager = AliasManager(repo)

    target_user_id = user_id
    user = _find_optional_by_id(users, "user_id", target_user_id) if target_user_id else None
    if user is None:
        target_user_id = _next_user_id(users)
        user = UserIdentity(
            user_id=target_user_id,
            canonical_name=draft.proposed_name,
            user_type=draft.proposed_user_type,
            relationship_to_me=draft.relationship_to_me,
            status="confirmed",
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )
        users.append(user)
    else:
        if not user.canonical_name:
            user.canonical_name = draft.proposed_name
        if user.user_type == "未知" and draft.proposed_user_type:
            user.user_type = draft.proposed_user_type
        if user.relationship_to_me == "未知" and draft.relationship_to_me:
            user.relationship_to_me = draft.relationship_to_me
        user.updated_at = draft.updated_at or user.updated_at

    draft.status = "confirmed"
    draft.updated_at = draft.updated_at or user.updated_at

    repo.save_users(users)
    repo.save_draft_users(drafts)
    alias_manager.add_alias(
        user_id=target_user_id,
        display_name=draft.proposed_name,
        updated_at=draft.updated_at,
    )
    alias = _load_alias_document(repo, target_user_id)
    return {"draft": asdict(draft), "user": asdict(user), "alias": alias}


def merge_candidate(candidate_id: str, *, base_dir: Path | str | None = None) -> dict[str, Any]:
    repo = _repository(base_dir)
    candidates = repo.load_candidates()
    candidate = _find_by_id(candidates, "candidate_id", candidate_id)
    alias_manager = AliasManager(repo)
    alias_manager.add_alias(
        user_id=candidate.matched_user_id,
        display_name=candidate.incoming_name,
    )
    candidate.status = "merged"
    repo.save_candidates(candidates)
    return {"candidate": asdict(candidate), "alias": _load_alias_document(repo, candidate.matched_user_id)}


def add_alias(
    user_id: str,
    name: str,
    *,
    group_name: str | None = None,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    repo = _repository(base_dir)
    _find_by_id(repo.load_users(), "user_id", user_id)
    AliasManager(repo).add_alias(user_id=user_id, display_name=name, group_name=group_name)
    return _load_alias_document(repo, user_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review and confirm WeChat identity drafts and candidates.")
    parser.add_argument("--base-dir", type=Path, default=None, help="Identity data root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-users", help="List confirmed identity users")
    subparsers.add_parser("list-drafts", help="List draft users awaiting confirmation")
    subparsers.add_parser("list-candidates", help="List identity match candidates awaiting merge")

    confirm_parser = subparsers.add_parser("confirm-draft", help="Confirm one draft into a user")
    confirm_parser.add_argument("--draft-id", required=True)
    confirm_parser.add_argument("--user-id", default=None)

    merge_parser = subparsers.add_parser("merge-candidate", help="Merge one candidate into aliases")
    merge_parser.add_argument("--candidate-id", required=True)

    alias_parser = subparsers.add_parser("add-alias", help="Add an alias to a confirmed user")
    alias_parser.add_argument("--user-id", required=True)
    alias_parser.add_argument("--name", required=True)
    alias_parser.add_argument("--group-name", default=None)

    args = parser.parse_args(argv)
    if args.command == "list-users":
        payload: Any = list_users(base_dir=args.base_dir)
    elif args.command == "list-drafts":
        payload = list_drafts(base_dir=args.base_dir)
    elif args.command == "list-candidates":
        payload = list_candidates(base_dir=args.base_dir)
    elif args.command == "confirm-draft":
        payload = confirm_draft(args.draft_id, user_id=args.user_id, base_dir=args.base_dir)
    elif args.command == "merge-candidate":
        payload = merge_candidate(args.candidate_id, base_dir=args.base_dir)
    else:
        payload = add_alias(args.user_id, args.name, group_name=args.group_name, base_dir=args.base_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _repository(base_dir: Path | str | None) -> IdentityRepository:
    return IdentityRepository(base_dir=Path(base_dir) if base_dir is not None else None)


def _find_by_id(items: list[Any], field_name: str, value: str | None) -> Any:
    item = _find_optional_by_id(items, field_name, value)
    if item is None:
        raise ValueError(f"{field_name} not found: {value}")
    return item


def _find_optional_by_id(items: list[Any], field_name: str, value: str | None) -> Any:
    if value is None:
        return None
    return next((item for item in items if getattr(item, field_name) == value), None)


def _load_alias_document(repo: IdentityRepository, user_id: str) -> dict[str, Any]:
    alias = _find_optional_by_id(repo.load_aliases(), "user_id", user_id)
    if alias is None:
        return {
            "user_id": user_id,
            "display_names": [],
            "remarks": [],
            "group_nicknames": [],
            "latest_seen_name": "",
            "updated_at": "",
        }
    return asdict(alias)


def _next_user_id(users: list[UserIdentity]) -> str:
    next_number = 1
    for user in users:
        prefix, _, suffix = user.user_id.partition("_")
        if prefix != "user" or not suffix.isdigit():
            continue
        next_number = max(next_number, int(suffix) + 1)
    return f"user_{next_number:06d}"


if __name__ == "__main__":
    raise SystemExit(main())
