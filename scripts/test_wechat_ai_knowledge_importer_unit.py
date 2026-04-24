from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


def _fresh_dir(prefix: str) -> Path:
    path = TMP_ROOT / prefix.lstrip(".") / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


class KnowledgeImporterTests(TestCase):
    def test_import_txt_file_copies_and_rebuilds_index(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter

        root = _fresh_dir(".tmp_knowledge_importer_txt")
        try:
            source = root / "faq.txt"
            source.write_text("退款说明：支持 7 天内申请。", encoding="utf-8")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            result = importer.import_files([source])
            self.assertEqual(result.files[0].status, "imported")
            self.assertTrue((root / "knowledge" / "uploads" / "originals" / "faq.txt").exists())
            self.assertTrue((root / "knowledge" / "local_knowledge_index.json").exists())
            self.assertIsNotNone(result.index_status)
            self.assertTrue(result.index_status.ready)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_import_unknown_extension_reports_unsupported(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter

        root = _fresh_dir(".tmp_knowledge_importer_unsupported")
        try:
            source = root / "archive.zip"
            source.write_bytes(b"fake")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            result = importer.import_files([source], rebuild_index=False)
            self.assertEqual(result.files[0].status, "unsupported")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_import_pdf_uses_extracted_text_for_indexing(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter
        from wechat_ai.rag.retriever import LocalIndexRetriever
        from wechat_ai.rag.embeddings import FakeEmbeddings

        root = _fresh_dir(".tmp_knowledge_importer_pdf")
        try:
            source = root / "manual.pdf"
            source.write_bytes(b"%PDF-fake")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            importer.document_registry.extract = lambda path: type("Extracted", (), {
                "source_path": Path(path),
                "text": "退款规则：支持7天内申请，审核通过后原路退回。",
                "suggested_title": "退款手册",
            })()

            result = importer.import_files([source])
            self.assertEqual(result.files[0].status, "imported")
            extracted_dir = root / "knowledge" / "uploads" / "extracted"
            extracted_files = list(extracted_dir.glob("manual*.md"))
            self.assertEqual(len(extracted_files), 1)
            self.assertIn("退款规则", extracted_files[0].read_text(encoding="utf-8"))

            retriever = LocalIndexRetriever(index_path=root / "knowledge" / "local_knowledge_index.json", embeddings=FakeEmbeddings())
            retrieved = retriever.retrieve("退款怎么申请", limit=1)
            self.assertEqual(len(retrieved), 1)
            self.assertIn("退款规则", retrieved[0].text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_import_image_and_docx_are_supported_extensions(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter

        root = _fresh_dir(".tmp_knowledge_importer_multiformat")
        try:
            image = root / "faq.png"
            image.write_bytes(b"fake-image")
            docx = root / "guide.docx"
            docx.write_bytes(b"fake-docx")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            importer.document_registry.extract = lambda path: type("Extracted", (), {
                "source_path": Path(path),
                "text": f"{Path(path).stem} 内容",
                "suggested_title": Path(path).stem,
            })()
            result = importer.import_files([image, docx], rebuild_index=False)
            self.assertEqual([item.status for item in result.files], ["imported", "imported"])
            status = importer.get_status()
            self.assertIn(".png", status.supported_extensions)
            self.assertIn(".docx", status.supported_extensions)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_import_missing_file_reports_missing(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter

        root = _fresh_dir(".tmp_knowledge_importer_missing")
        try:
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            result = importer.import_files([root / "missing.md"], rebuild_index=False)
            self.assertEqual(result.files[0].status, "missing")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_list_files_and_status(self) -> None:
        from wechat_ai.app.knowledge_importer import KnowledgeImporter

        root = _fresh_dir(".tmp_knowledge_importer_status")
        try:
            source = root / "note.md"
            source.write_text("# 标题\n内容", encoding="utf-8")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            importer.import_files([source])
            files = importer.list_files()
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].file_name, "note.md")
            status = importer.get_status()
            self.assertTrue(status.ready)
            self.assertGreaterEqual(status.documents_loaded, 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
