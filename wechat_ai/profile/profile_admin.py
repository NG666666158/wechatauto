from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .profile_store import ProfileStore
from .tag_manager import TagManager


_LIST_FIELDS = {"tags", "style_rules", "goals", "forbidden_rules"}
_KINDS = {"user", "agent"}


def list_profile_documents(kind: str, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    store = _store(base_dir)
    directory = _profile_dir(store, kind)
    if not directory.exists():
        return []
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            documents.append(json.load(handle))
    return documents


def load_profile_document(kind: str, profile_id: str, base_dir: Path | str | None = None) -> dict[str, Any]:
    store = _store(base_dir)
    profile = _load_profile(store, kind, profile_id)
    return _profile_to_document(profile)


def update_profile_document(
    kind: str,
    profile_id: str,
    updates: dict[str, Any],
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    store = _store(base_dir)
    profile = _load_profile(store, kind, profile_id)
    for field_name, value in updates.items():
        if not hasattr(profile, field_name):
            raise ValueError(f"Unknown {kind} profile field: {field_name}")
        setattr(profile, field_name, _normalize_update_value(field_name, value))
    _save_profile(store, kind, profile)
    return load_profile_document(kind, profile_id, base_dir=base_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and edit WeChat AI profile documents.")
    parser.add_argument("--base-dir", type=Path, default=None, help="Profile data root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List profile documents")
    list_parser.add_argument("--kind", choices=sorted(_KINDS), required=True)

    show_parser = subparsers.add_parser("show", help="Show one profile document")
    show_parser.add_argument("--kind", choices=sorted(_KINDS), required=True)
    show_parser.add_argument("--id", required=True, dest="profile_id")

    set_parser = subparsers.add_parser("set", help="Set one top-level profile field")
    set_parser.add_argument("--kind", choices=sorted(_KINDS), required=True)
    set_parser.add_argument("--id", required=True, dest="profile_id")
    set_parser.add_argument("--field", required=True)
    set_parser.add_argument("--value", required=True)

    args = parser.parse_args(argv)
    if args.command == "list":
        payload: Any = list_profile_documents(args.kind, base_dir=args.base_dir)
    elif args.command == "show":
        payload = load_profile_document(args.kind, args.profile_id, base_dir=args.base_dir)
    else:
        payload = update_profile_document(
            args.kind,
            args.profile_id,
            {args.field: args.value},
            base_dir=args.base_dir,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _store(base_dir: Path | str | None) -> ProfileStore:
    return ProfileStore(base_dir=Path(base_dir) if base_dir is not None else None)


def _validate_kind(kind: str) -> str:
    if kind not in _KINDS:
        raise ValueError("kind must be 'user' or 'agent'")
    return kind


def _profile_dir(store: ProfileStore, kind: str) -> Path:
    kind = _validate_kind(kind)
    return store.user_profiles_dir if kind == "user" else store.agent_profiles_dir


def _load_profile(store: ProfileStore, kind: str, profile_id: str) -> Any:
    kind = _validate_kind(kind)
    return store.load_user_profile(profile_id) if kind == "user" else store.load_agent_profile(profile_id)


def _save_profile(store: ProfileStore, kind: str, profile: Any) -> None:
    kind = _validate_kind(kind)
    if kind == "user":
        store.save_user_profile(profile)
    else:
        store.save_agent_profile(profile)


def _profile_to_document(profile: Any) -> dict[str, Any]:
    if is_dataclass(profile):
        return asdict(profile)
    return {key: value for key, value in vars(profile).items() if not key.startswith("_")}


def _normalize_update_value(field_name: str, value: Any) -> Any:
    if field_name not in _LIST_FIELDS:
        return value
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        items = [item.strip() for item in value if isinstance(item, str)]
    else:
        items = []
    items = [item for item in items if item]
    if field_name == "tags":
        return TagManager.normalize(items)
    return items


if __name__ == "__main__":
    raise SystemExit(main())
