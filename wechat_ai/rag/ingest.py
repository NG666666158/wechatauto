from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from wechat_ai import paths
from wechat_ai.rag.chunker import Chunker
from wechat_ai.rag.embeddings import FakeEmbeddings
from wechat_ai.rag.knowledge_store import KnowledgeDocument, normalize_document


SUPPORTED_EXTENSIONS = {".json", ".md", ".txt"}


def iter_knowledge_paths(
    root_dir: Path | None = None,
    source_paths: Iterable[Path] | None = None,
) -> list[Path]:
    knowledge_dir = Path(root_dir or paths.KNOWLEDGE_DIR)
    if not knowledge_dir.exists():
        return []

    if source_paths is None:
        candidates = [path for path in knowledge_dir.rglob("*") if path.is_file()]
    else:
        candidates = [Path(path) for path in source_paths if Path(path).is_file()]

    return sorted(path for path in candidates if path.suffix.lower() in SUPPORTED_EXTENSIONS)


def load_knowledge_documents(
    root_dir: Path | None = None,
    source_paths: Iterable[Path] | None = None,
) -> list[KnowledgeDocument]:
    knowledge_dir = Path(root_dir or paths.KNOWLEDGE_DIR)
    if not knowledge_dir.exists():
        return []

    documents: list[KnowledgeDocument] = []
    for source_path in iter_knowledge_paths(knowledge_dir, source_paths):
        if source_path.suffix.lower() == ".json":
            document = _load_json_document(source_path, knowledge_dir)
        else:
            document = _load_text_document(source_path, knowledge_dir)

        if document is not None:
            documents.append(document)

    return documents


def build_knowledge_index(
    *,
    knowledge_dir: Path | None = None,
    index_path: Path,
    chunk_size: int,
    overlap: int,
    source_paths: Iterable[Path] | None = None,
) -> dict[str, object]:
    resolved_knowledge_dir = Path(knowledge_dir or paths.KNOWLEDGE_DIR)
    resolved_knowledge_dir.mkdir(parents=True, exist_ok=True)

    resolved_index_path = Path(index_path)
    resolved_index_path.parent.mkdir(parents=True, exist_ok=True)

    documents = load_knowledge_documents(root_dir=resolved_knowledge_dir, source_paths=source_paths)
    chunker = Chunker(chunk_size=chunk_size, overlap=overlap)

    chunks: list[dict[str, object]] = []
    for document in documents:
        chunks.extend(chunker.chunk_document(document))

    embeddings = FakeEmbeddings()
    vectors = embeddings.embed_documents([chunk["text"] for chunk in chunks]) if chunks else []

    payload = {
        "schema_version": 1,
        "knowledge_dir": str(resolved_knowledge_dir),
        "embedding_provider": embeddings.__class__.__name__,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "chunks": [
            {
                **chunk,
                "metadata": {
                    "doc_id": chunk["doc_id"],
                    "title": chunk["title"],
                    "source": chunk["source"],
                    "chunk_index": str(chunk["chunk_index"]),
                },
                "vector": vector,
            }
            for chunk, vector in zip(chunks, vectors)
        ],
    }

    resolved_index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "index_path": resolved_index_path,
        "knowledge_dir": resolved_knowledge_dir,
    }


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
