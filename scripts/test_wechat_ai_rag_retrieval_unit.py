from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai import RetrievedChunk  # type: ignore  # noqa: E402
from wechat_ai.rag.embeddings import BaseEmbeddings  # type: ignore  # noqa: E402
from wechat_ai.rag.reranker import NoOpReranker  # type: ignore  # noqa: E402
from wechat_ai.rag.retriever import LocalIndexRetriever  # type: ignore  # noqa: E402


class SemanticTestEmbeddings(BaseEmbeddings):
    def __init__(self) -> None:
        self._vectors = {
            "billing support price refund": [1.0, 0.0, 0.0],
            "installation setup guide windows": [0.0, 1.0, 0.0],
            "account reset password login": [0.0, 0.0, 1.0],
            "how do i get a refund for billing": [0.9, 0.1, 0.0],
        }

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[text] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vectors[text]


class LocalIndexRetrieverTests(unittest.TestCase):
    def _make_temp_dir(self) -> Path:
        root = ROOT / ".tmp_wechat_ai_rag_retrieval"
        root.mkdir(exist_ok=True)
        return root

    def test_retrieve_returns_retrieved_chunks_in_cosine_similarity_order(self) -> None:
        temp_dir = self._make_temp_dir()
        index_path = temp_dir / "knowledge_index.json"
        payload = {
            "chunks": [
                {
                    "text": "billing support price refund",
                    "vector": [1.0, 0.0, 0.0],
                    "metadata": {
                        "doc_id": "faq",
                        "title": "Billing FAQ",
                        "source": "wechat_ai/data/knowledge/faq.md",
                        "chunk_index": "0",
                    },
                },
                {
                    "text": "installation setup guide windows",
                    "vector": [0.0, 1.0, 0.0],
                    "metadata": {
                        "doc_id": "install",
                        "title": "Install Guide",
                        "source": "wechat_ai/data/knowledge/install.md",
                        "chunk_index": "0",
                    },
                },
                {
                    "text": "account reset password login",
                    "vector": [0.0, 0.0, 1.0],
                    "metadata": {
                        "doc_id": "account",
                        "title": "Account Help",
                        "source": "wechat_ai/data/knowledge/account.md",
                        "chunk_index": "0",
                    },
                },
            ]
        }
        index_path.write_text(json.dumps(payload), encoding="utf-8")

        retriever = LocalIndexRetriever(
            index_path=index_path,
            embeddings=SemanticTestEmbeddings(),
        )

        chunks = retriever.retrieve("how do i get a refund for billing", limit=2)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(isinstance(chunk, RetrievedChunk) for chunk in chunks))
        self.assertEqual(chunks[0].text, "billing support price refund")
        self.assertEqual(chunks[0].metadata["doc_id"], "faq")
        self.assertGreater(chunks[0].score, chunks[1].score)
        self.assertEqual(chunks[1].text, "installation setup guide windows")

    def test_retrieve_uses_no_op_reranker_interface_without_changing_order(self) -> None:
        temp_dir = self._make_temp_dir()
        index_path = temp_dir / "knowledge_index.json"
        index_path.write_text(
            json.dumps(
                {
                    "chunks": [
                        {
                            "text": "billing support price refund",
                            "vector": [1.0, 0.0, 0.0],
                            "metadata": {"doc_id": "faq"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        retriever = LocalIndexRetriever(
            index_path=index_path,
            embeddings=SemanticTestEmbeddings(),
            reranker=NoOpReranker(),
        )

        chunks = retriever.retrieve("how do i get a refund for billing", limit=1)

        self.assertEqual([chunk.text for chunk in chunks], ["billing support price refund"])

if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(LocalIndexRetrieverTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
