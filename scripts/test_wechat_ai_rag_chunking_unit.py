from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.rag.chunker import Chunker  # type: ignore  # noqa: E402
from wechat_ai.rag.embeddings import BaseEmbeddings, FakeEmbeddings  # type: ignore  # noqa: E402


class ChunkerTests(unittest.TestCase):
    def test_short_document_passes_through_as_single_chunk(self) -> None:
        chunker = Chunker(chunk_size=50, overlap=10)

        chunks = chunker.chunk_document(
            {
                "doc_id": "doc-1",
                "title": "FAQ",
                "source": "knowledge/faq.md",
                "text": "short document",
            }
        )

        self.assertEqual(
            chunks,
            [
                {
                    "doc_id": "doc-1",
                    "title": "FAQ",
                    "source": "knowledge/faq.md",
                    "chunk_index": 0,
                    "text": "short document",
                }
            ],
        )

    def test_multi_chunk_output_preserves_overlap_and_metadata(self) -> None:
        chunker = Chunker(chunk_size=6, overlap=2)

        chunks = chunker.chunk_document(
            {
                "doc_id": "doc-2",
                "title": "Guide",
                "source": "knowledge/guide.txt",
                "text": "abcdefghijkl",
            }
        )

        self.assertEqual(
            chunks,
            [
                {
                    "doc_id": "doc-2",
                    "title": "Guide",
                    "source": "knowledge/guide.txt",
                    "chunk_index": 0,
                    "text": "abcdef",
                },
                {
                    "doc_id": "doc-2",
                    "title": "Guide",
                    "source": "knowledge/guide.txt",
                    "chunk_index": 1,
                    "text": "efghij",
                },
                {
                    "doc_id": "doc-2",
                    "title": "Guide",
                    "source": "knowledge/guide.txt",
                    "chunk_index": 2,
                    "text": "ijkl",
                },
            ],
        )

    def test_invalid_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Chunker(chunk_size=5, overlap=5)


class EmbeddingsTests(unittest.TestCase):
    def test_base_embeddings_requires_implementation(self) -> None:
        provider = BaseEmbeddings()

        with self.assertRaises(NotImplementedError):
            provider.embed_documents(["hello"])
        with self.assertRaises(NotImplementedError):
            provider.embed_query("hello")

    def test_fake_embeddings_are_deterministic_for_documents_and_queries(self) -> None:
        provider = FakeEmbeddings(dimensions=6)

        document_vectors = provider.embed_documents(["alpha", "beta", "alpha"])
        query_vector = provider.embed_query("alpha")

        self.assertEqual(len(document_vectors), 3)
        self.assertEqual(len(document_vectors[0]), 6)
        self.assertEqual(document_vectors[0], document_vectors[2])
        self.assertEqual(document_vectors[0], query_vector)
        self.assertNotEqual(document_vectors[0], document_vectors[1])


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ChunkerTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(EmbeddingsTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
