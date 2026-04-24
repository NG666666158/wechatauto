from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _fresh_dir(prefix: str) -> Path:
    path = ROOT / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeDocumentRegistry:
    def extract(self, source_path: Path | str):
        path = Path(source_path)
        return type(
            "Extracted",
            (),
            {
                "source_path": path,
                "text": "智能客服系统建设方案，关注自动回复、FAQ、工单流转与知识库。",
                "suggested_title": "智能客服方案",
            },
        )()


class WebKnowledgeBuilderTests(TestCase):
    def test_build_from_document_fetches_pages_and_imports_them(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter
        from wechat_ai.rag.web_knowledge_builder import WebKnowledgeBuilder

        root = _fresh_dir(".tmp_web_knowledge_builder")
        try:
            seed = root / "seed.docx"
            seed.write_bytes(b"fake-docx")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
                document_registry=FakeDocumentRegistry(),
            )
            builder = WebKnowledgeBuilder(
                knowledge_dir=root / "knowledge",
                knowledge_importer=importer,
                document_registry=FakeDocumentRegistry(),
                search_client=lambda query, limit: [
                    {
                        "title": "2026 智能客服知识库最佳实践",
                        "url": "https://example.com/best-practices",
                        "snippet": "围绕FAQ与自动回复。",
                    },
                    {
                        "title": "客服知识库维护指南",
                        "url": "https://example.com/maintenance",
                        "snippet": "介绍知识库分层更新。",
                    },
                ][:limit],
                fetch_client=lambda url: {
                    "url": url,
                    "title": "抓取页面",
                    "content": f"{url} 提到自动回复、FAQ、检索和人工接管。",
                },
            )

            result = builder.build_from_documents([seed], search_limit=2)
            self.assertEqual(result["seed_documents"], 1)
            self.assertEqual(result["fetched_count"], 2)
            self.assertEqual(result["imported_count"], 2)
            self.assertTrue(result["index_status"]["ready"])
            stored_files = list((root / "knowledge" / "web" / "fetched").glob("*.md"))
            self.assertEqual(len(stored_files), 2)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_duckduckgo_protocol_relative_redirect_is_normalized(self) -> None:
        from wechat_ai.rag.web_knowledge_builder import _normalize_candidate_url

        raw = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fguide&rut=abc"
        normalized = _normalize_candidate_url(raw)
        self.assertEqual(normalized, "https://example.com/guide")


def main() -> None:
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
