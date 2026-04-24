from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _fresh_dir(prefix: str) -> Path:
    path = ROOT / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class DocumentExtractorsTests(TestCase):
    def test_extract_json_uses_text_field(self) -> None:
        from wechat_ai.rag.document_extractors import DocumentExtractorRegistry

        root = _fresh_dir(".tmp_document_extractors_json")
        try:
            source = root / "faq.json"
            source.write_text('{"title":"FAQ","text":"退款支持7天内申请"}', encoding="utf-8")
            extracted = DocumentExtractorRegistry().extract(source)
            self.assertEqual(extracted.suggested_title, "faq")
            self.assertIn("退款支持", extracted.text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_extract_pdf_uses_pypdf_reader(self) -> None:
        from wechat_ai.rag.document_extractors import DocumentExtractorRegistry

        root = _fresh_dir(".tmp_document_extractors_pdf")
        try:
            source = root / "guide.pdf"
            source.write_bytes(b"%PDF-test")

            class FakePage:
                def __init__(self, text: str) -> None:
                    self._text = text

                def extract_text(self) -> str:
                    return self._text

            class FakeReader:
                def __init__(self, path: str) -> None:
                    self.pages = [FakePage("第一页"), FakePage("第二页")]

            with patch("wechat_ai.rag.document_extractors._import_optional", return_value=FakeReader):
                extracted = DocumentExtractorRegistry().extract(source)
            self.assertIn("第一页", extracted.text)
            self.assertIn("第二页", extracted.text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_extract_docx_uses_python_docx_document(self) -> None:
        from wechat_ai.rag.document_extractors import DocumentExtractorRegistry

        root = _fresh_dir(".tmp_document_extractors_docx")
        try:
            source = root / "guide.docx"
            source.write_bytes(b"fake-docx")

            class FakeParagraph:
                def __init__(self, text: str) -> None:
                    self.text = text

            class FakeDocument:
                def __init__(self, path: str) -> None:
                    self.paragraphs = [FakeParagraph("段落一"), FakeParagraph(""), FakeParagraph("段落二")]

            with patch("wechat_ai.rag.document_extractors._import_optional", return_value=FakeDocument):
                extracted = DocumentExtractorRegistry().extract(source)
            self.assertEqual(extracted.text, "段落一\n\n段落二")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_extract_image_uses_windows_ocr_output(self) -> None:
        from wechat_ai.rag.document_extractors import DocumentExtractorRegistry

        root = _fresh_dir(".tmp_document_extractors_image")
        try:
            source = root / "faq.png"
            source.write_bytes(b"fake-image")

            class Completed:
                returncode = 0
                stdout = "识别出的图片文字"
                stderr = ""

            with patch("wechat_ai.rag.document_extractors.subprocess.run", return_value=Completed()):
                extracted = DocumentExtractorRegistry().extract(source)
            self.assertEqual(extracted.text, "识别出的图片文字")
        finally:
            shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
