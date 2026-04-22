from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wechat_ai import RetrievedChunk
from wechat_ai.rag.embeddings import BaseEmbeddings
from wechat_ai.rag.reranker import BaseReranker, NoOpReranker


@dataclass(frozen=True)
class LocalIndexRetriever:
    index_path: Path
    embeddings: BaseEmbeddings
    reranker: BaseReranker = field(default_factory=NoOpReranker)

    def retrieve(self, query: str, limit: int = 3) -> list[RetrievedChunk]:
        if limit <= 0:
            return []

        query_vector = self.embeddings.embed_query(query)
        scored_chunks: list[RetrievedChunk] = []
        for chunk in self._load_chunks():
            score = _cosine_similarity(query_vector, chunk["vector"])
            scored_chunks.append(
                RetrievedChunk(
                    text=chunk["text"],
                    score=score,
                    metadata=_normalize_metadata(chunk.get("metadata", {})),
                )
            )

        ranked_chunks = sorted(scored_chunks, key=lambda chunk: chunk.score, reverse=True)
        return self.reranker.rerank(query, ranked_chunks[:limit])

    def _load_chunks(self) -> list[dict[str, Any]]:
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        chunks = payload.get("chunks", [])
        if not isinstance(chunks, list):
            raise ValueError("index payload must contain a 'chunks' list")
        return [chunk for chunk in chunks if isinstance(chunk, dict)]


def _normalize_metadata(metadata: object) -> dict[str, str]:
    if not isinstance(metadata, dict):
        return {}
    return {str(key): str(value) for key, value in metadata.items()}


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot_product / (left_norm * right_norm)
