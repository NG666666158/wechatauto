from __future__ import annotations

from pathlib import Path


KnowledgeDocument = dict[str, str]


def normalize_document(
    *,
    source_path: Path,
    root_dir: Path,
    text: str,
    doc_id: str | None = None,
    title: str | None = None,
    category: str | None = None,
) -> KnowledgeDocument | None:
    clean_text = text.strip()
    if not clean_text:
        return None

    resolved_root = root_dir.resolve()
    relative_source = source_path.resolve().relative_to(resolved_root).as_posix()
    stem = source_path.stem

    return {
        "doc_id": (doc_id or stem).strip() or stem,
        "title": (title or stem).strip() or stem,
        "source": f"wechat_ai/data/knowledge/{relative_source}",
        "text": clean_text,
        "category": (category or stem).strip() or stem,
    }
