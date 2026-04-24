from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


TextExtractor = Callable[[Path], str]


@dataclass(frozen=True)
class ExtractedDocument:
    source_path: Path
    text: str
    suggested_title: str | None = None


SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".json"}
SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
SUPPORTED_SOURCE_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS


class DocumentExtractorRegistry:
    def __init__(self) -> None:
        self._extractors: dict[str, TextExtractor] = {
            ".txt": self._extract_plain_text,
            ".md": self._extract_plain_text,
            ".json": self._extract_json_text,
            ".pdf": self._extract_pdf_text,
            ".docx": self._extract_docx_text,
        }
        for extension in SUPPORTED_IMAGE_EXTENSIONS:
            self._extractors[extension] = self._extract_image_text

    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._extractors.keys()))

    def extract(self, source_path: Path | str) -> ExtractedDocument:
        path = Path(source_path)
        extension = path.suffix.lower()
        extractor = self._extractors.get(extension)
        if extractor is None:
            raise ValueError(f"unsupported extension: {extension or '<none>'}")
        text = extractor(path)
        return ExtractedDocument(source_path=path, text=text.strip(), suggested_title=path.stem)

    def _extract_plain_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _extract_json_text(self, path: Path) -> str:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return str(payload.get("text", "")).strip()
        return ""

    def _extract_pdf_text(self, path: Path) -> str:
        PdfReader = _import_optional("pypdf", "PdfReader")
        reader = PdfReader(str(path))
        return "\n\n".join(
            (page.extract_text() or "").strip()
            for page in reader.pages
            if (page.extract_text() or "").strip()
        )

    def _extract_docx_text(self, path: Path) -> str:
        Document = _import_optional("docx", "Document")
        document = Document(str(path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)

    def _extract_image_text(self, path: Path) -> str:
        completed = subprocess.run(
            _build_windows_ocr_command(path),
            capture_output=True,
            text=True,
            check=False,
        )
        text = (completed.stdout or "").strip()
        if completed.returncode != 0 or not text:
            stderr = (completed.stderr or "").strip()
            raise RuntimeError(f"image OCR failed: {stderr or 'no text recognized'}")
        return text


def _import_optional(module_name: str, attr_name: str):
    try:
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    except ModuleNotFoundError:
        runtime_site = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python"
        if runtime_site.exists() and str(runtime_site) not in sys.path:
            sys.path.append(str(runtime_site))
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)


def _build_windows_ocr_command(path: Path) -> list[str]:
    normalized = str(path).replace("'", "''")
    script = rf"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.RandomAccessStreamReference,Windows.Foundation,ContentType=WindowsRuntime]

function Await([object]$task) {{
  $task.AsTask().GetAwaiter().GetResult()
}}

$file = Await([Windows.Storage.StorageFile]::GetFileFromPathAsync('{normalized}'))
$stream = Await($file.OpenAsync([Windows.Storage.FileAccessMode]::Read))
$decoder = Await([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
$bitmap = Await($decoder.GetSoftwareBitmapAsync())
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$result = Await($engine.RecognizeAsync($bitmap))
Write-Output $result.Text
"""
    compact = re.sub(r"\s+", " ", script).strip()
    return ["powershell", "-NoProfile", "-Command", compact]
