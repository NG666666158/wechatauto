from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_INDEX_FILENAME = "local_knowledge_index.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load local knowledge files and build a JSON knowledge index."
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="Optional output path for the generated JSON index.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum characters per chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Character overlap between adjacent chunks.",
    )
    return parser.parse_args()


def resolve_dependencies() -> dict[str, Any]:
    try:
        from wechat_ai import paths
        from wechat_ai.rag.chunker import Chunker
        from wechat_ai.rag.embeddings import FakeEmbeddings
        from wechat_ai.rag.ingest import load_knowledge_documents
    except ImportError as exc:
        raise RuntimeError(
            "Missing lower-level RAG modules required for ingestion. "
            f"Import failed: {exc}"
        ) from exc

    return {
        "paths": paths,
        "Chunker": Chunker,
        "FakeEmbeddings": FakeEmbeddings,
        "load_knowledge_documents": load_knowledge_documents,
    }


def default_index_path(paths_module: Any) -> Path:
    return Path(paths_module.KNOWLEDGE_DIR) / DEFAULT_INDEX_FILENAME


def build_index(*, index_path: Path | None, chunk_size: int, overlap: int) -> dict[str, Any]:
    deps = resolve_dependencies()
    paths_module = deps["paths"]
    paths_module.bootstrap_data_dirs()

    resolved_index_path = Path(index_path) if index_path is not None else default_index_path(paths_module)
    resolved_index_path.parent.mkdir(parents=True, exist_ok=True)

    documents = deps["load_knowledge_documents"]()
    chunker = deps["Chunker"](chunk_size=chunk_size, overlap=overlap)

    chunks: list[dict[str, Any]] = []
    for document in documents:
        chunks.extend(chunker.chunk_document(document))

    embeddings = deps["FakeEmbeddings"]()
    vectors = embeddings.embed_documents([chunk["text"] for chunk in chunks]) if chunks else []

    payload = {
        "schema_version": 1,
        "knowledge_dir": str(paths_module.KNOWLEDGE_DIR),
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

    resolved_index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "index_path": resolved_index_path,
    }


def print_summary(summary: dict[str, Any], *, prefix: str = "Knowledge index built.") -> None:
    print(prefix)
    print(f"documents loaded: {summary['documents_loaded']}")
    print(f"chunks created: {summary['chunks_created']}")
    print(f"index file path: {summary['index_path']}")


def main() -> int:
    args = parse_args()
    try:
        summary = build_index(
            index_path=args.index_path,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except Exception as exc:
        print(f"Knowledge index build failed: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
