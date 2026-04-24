from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def test_loads_markdown_text_and_json_documents() -> None:
    from wechat_ai.rag.ingest import load_knowledge_documents

    scratch_dir = TMP_ROOT / "wechat_ai_rag_loading" / "knowledge"
    _reset_dir(scratch_dir)

    try:
        (scratch_dir / "faq.md").write_text("# FAQ\n\nAnswer one.", encoding="utf-8")
        (scratch_dir / "notes.txt").write_text("Plain text note.", encoding="utf-8")
        (scratch_dir / "guide.json").write_text(
            json.dumps(
                {
                    "doc_id": "guide_001",
                    "title": "Guide",
                    "text": "JSON body",
                    "category": "manual",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        documents = load_knowledge_documents(scratch_dir)

        assert len(documents) == 3
        assert documents[0] == {
            "doc_id": "faq",
            "title": "FAQ",
            "source": "wechat_ai/data/knowledge/faq.md",
            "text": "# FAQ\n\nAnswer one.",
            "category": "faq",
        }
        assert documents[1] == {
            "doc_id": "guide_001",
            "title": "Guide",
            "source": "wechat_ai/data/knowledge/guide.json",
            "text": "JSON body",
            "category": "manual",
        }
        assert documents[2] == {
            "doc_id": "notes",
            "title": "notes",
            "source": "wechat_ai/data/knowledge/notes.txt",
            "text": "Plain text note.",
            "category": "notes",
        }
    finally:
        shutil.rmtree(scratch_dir.parent, ignore_errors=True)


def test_ignores_empty_files() -> None:
    from wechat_ai.rag.ingest import load_knowledge_documents

    scratch_dir = TMP_ROOT / "wechat_ai_rag_loading_empty" / "knowledge"
    _reset_dir(scratch_dir)

    try:
        (scratch_dir / "blank.txt").write_text("   \n", encoding="utf-8")
        (scratch_dir / "filled.txt").write_text("keep me", encoding="utf-8")

        documents = load_knowledge_documents(scratch_dir)

        assert len(documents) == 1
        assert documents[0]["doc_id"] == "filled"
    finally:
        shutil.rmtree(scratch_dir.parent, ignore_errors=True)


def test_invalid_json_raises_readable_error() -> None:
    from wechat_ai.rag.ingest import load_knowledge_documents

    scratch_dir = TMP_ROOT / "wechat_ai_rag_loading_invalid" / "knowledge"
    _reset_dir(scratch_dir)

    try:
        (scratch_dir / "broken.json").write_text("{bad json", encoding="utf-8")

        try:
            load_knowledge_documents(scratch_dir)
        except ValueError as exc:
            message = str(exc)
            assert "Invalid JSON" in message
            assert "broken.json" in message
        else:
            raise AssertionError("Expected invalid JSON to raise ValueError")
    finally:
        shutil.rmtree(scratch_dir.parent, ignore_errors=True)


def main() -> None:
    test_loads_markdown_text_and_json_documents()
    test_ignores_empty_files()
    test_invalid_json_raises_readable_error()
    print("wechat_ai rag loading unit tests passed")


if __name__ == "__main__":
    main()
