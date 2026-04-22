from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class KnowledgeDocument(TypedDict):
    doc_id: str
    title: str
    source: str
    text: str


class DocumentChunk(TypedDict):
    doc_id: str
    title: str
    source: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class Chunker:
    chunk_size: int = 1000
    overlap: int = 200

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0:
            raise ValueError("overlap must be non-negative")
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

    def chunk_document(self, document: KnowledgeDocument) -> list[DocumentChunk]:
        text = document["text"]
        if text == "":
            return []

        step = self.chunk_size - self.overlap
        chunks: list[DocumentChunk] = []
        for chunk_index, start in enumerate(range(0, len(text), step)):
            chunk_text = text[start : start + self.chunk_size]
            if chunk_text == "":
                continue
            chunks.append(
                {
                    "doc_id": document["doc_id"],
                    "title": document["title"],
                    "source": document["source"],
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )
        return chunks
