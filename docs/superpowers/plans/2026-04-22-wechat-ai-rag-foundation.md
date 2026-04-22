# WeChat AI RAG Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local knowledge ingestion and retrieval layer that can supply relevant chunks to the auto-reply pipeline.

**Architecture:** Keep the first RAG version local and replaceable. Separate loading, chunking, embedding, index persistence, and retrieval so future provider swaps or vector-store upgrades do not require rewriting the reply pipeline.

**Tech Stack:** Python file IO, JSON manifests, pluggable embeddings interface, local vector/index storage.

---

### Task 1: Add Knowledge Document Loading

**Files:**
- Create: `wechat_ai/rag/ingest.py`
- Create: `wechat_ai/rag/knowledge_store.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Implement loaders for `.md`, `.txt`, and `.json` files located under `wechat_ai/data/knowledge`.
- [ ] Normalize loaded documents into a simple structure:

```python
{
    "doc_id": "faq_001",
    "title": "FAQ",
    "source": "wechat_ai/data/knowledge/faq.md",
    "text": "...",
    "category": "faq",
}
```

- [ ] Ignore empty files and surface invalid JSON with readable exceptions.
- [ ] Add unit tests for all three supported formats.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add knowledge document loaders"`

### Task 2: Add Chunking Strategy

**Files:**
- Create: `wechat_ai/rag/chunker.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Implement a chunker with configurable `chunk_size` and `overlap`.
- [ ] Preserve chunk metadata:
  - `doc_id`
  - `title`
  - `source`
  - `chunk_index`
- [ ] Add tests covering:
  - short document passthrough
  - multi-chunk output
  - overlap correctness
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add rag chunking"`

### Task 3: Add Embeddings Abstraction And Local Index Format

**Files:**
- Create: `wechat_ai/rag/embeddings.py`
- Modify: `wechat_ai/rag/knowledge_store.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Define a provider interface such as:

```python
class BaseEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError
```

- [ ] Add a deterministic fake/local implementation for tests.
- [ ] Persist the local index as JSON with vectors and metadata so ingestion can be rebuilt offline.
- [ ] Add tests for index write/read round-trips.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add rag embeddings abstraction"`

### Task 4: Implement Retrieval

**Files:**
- Create: `wechat_ai/rag/retriever.py`
- Create: `wechat_ai/rag/reranker.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Implement cosine-similarity retrieval over the persisted local index.
- [ ] Keep `reranker.py` as a thin no-op/stub interface for now so a later reranker can be added without reshaping the pipeline.
- [ ] Return `RetrievedChunk` objects from retrieval so the reply pipeline uses shared types.
- [ ] Add tests that prove a semantically matching query returns the expected top chunk order.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add local rag retrieval"`

### Task 5: Add Operator Scripts For Ingestion And Rebuild

**Files:**
- Create: `scripts/ingest_knowledge.py`
- Create: `scripts/rebuild_index.py`
- Modify: `README.md`

- [ ] Add a script that scans the knowledge directory, chunks documents, computes embeddings, and persists the index.
- [ ] Add a rebuild script that clears the old index and regenerates it from source documents.
- [ ] Print summary counts for:
  - documents loaded
  - chunks created
  - index file path
- [ ] Document both commands in `README.md`.
- [ ] Run:

```powershell
py -3 scripts\ingest_knowledge.py
py -3 scripts\rebuild_index.py
```

- [ ] Expected: summary output with non-zero chunk count when sample documents exist.
- [ ] Commit: `git commit -m "feat: add rag ingestion scripts"`
