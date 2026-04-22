from __future__ import annotations

import json
from pathlib import Path

from wechat_ai import paths
from wechat_ai.rag.knowledge_store import KnowledgeDocument, normalize_document


SUPPORTED_EXTENSIONS = {".json", ".md", ".txt"}


def load_knowledge_documents(root_dir: Path | None = None) -> list[KnowledgeDocument]:
    knowledge_dir = Path(root_dir or paths.KNOWLEDGE_DIR)
    if not knowledge_dir.exists():
        return []

    documents: list[KnowledgeDocument] = []
    for source_path in sorted(path for path in knowledge_dir.rglob("*") if path.is_file()):
        if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if source_path.suffix.lower() == ".json":
            document = _load_json_document(source_path, knowledge_dir)
        else:
            document = _load_text_document(source_path, knowledge_dir)

        if document is not None:
            documents.append(document)

    return documents


def _load_text_document(source_path: Path, root_dir: Path) -> KnowledgeDocument | None:
    text = source_path.read_text(encoding="utf-8")
    title = _extract_markdown_title(text) if source_path.suffix.lower() == ".md" else None
    return normalize_document(source_path=source_path, root_dir=root_dir, text=text, title=title)


def _load_json_document(source_path: Path, root_dir: Path) -> KnowledgeDocument | None:
    raw_text = source_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return None

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source_path.name}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid JSON in {source_path.name}: expected an object")

    text = str(payload.get("text", "")).strip()
    return normalize_document(
        source_path=source_path,
        root_dir=root_dir,
        text=text,
        doc_id=_optional_string(payload.get("doc_id")),
        title=_optional_string(payload.get("title")),
        category=_optional_string(payload.get("category")),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _extract_markdown_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
        break
    return None
