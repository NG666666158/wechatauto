from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from wechat_ai import paths
from wechat_ai.app.models import KnowledgeFileRecord, KnowledgeIndexStatus
from wechat_ai.rag.document_extractors import DocumentExtractorRegistry
from wechat_ai.rag.ingest import build_knowledge_index


@dataclass(slots=True)
class KnowledgeImportResult:
    files: list[KnowledgeFileRecord]
    imported_count: int = 0
    index_status: KnowledgeIndexStatus | None = None


class KnowledgeImporter:
    def __init__(
        self,
        *,
        knowledge_dir: Path | None = None,
        uploads_dir: Path | None = None,
        index_path: Path | None = None,
        chunk_size: int = 1000,
        overlap: int = 200,
        document_registry: DocumentExtractorRegistry | None = None,
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir or paths.KNOWLEDGE_DIR)
        self.uploads_dir = Path(uploads_dir or paths.KNOWLEDGE_UPLOADS_DIR)
        self.index_path = Path(index_path or (self.knowledge_dir / "local_knowledge_index.json"))
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.document_registry = document_registry or DocumentExtractorRegistry()

    def import_files(
        self,
        file_paths: Sequence[str | Path],
        rebuild_index: bool = True,
    ) -> KnowledgeImportResult:
        originals_dir = self.uploads_dir / "originals"
        extracted_dir = self.uploads_dir / "extracted"
        originals_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        files: list[KnowledgeFileRecord] = []
        imported_count = 0
        for raw_path in file_paths:
            source_path = Path(raw_path)
            extension = source_path.suffix.lower()
            if not source_path.exists():
                files.append(self._record_for(source_path, extension, status="missing"))
                continue
            if extension not in self._supported_extensions():
                files.append(
                    self._record_for(
                        source_path,
                        extension,
                        status="unsupported",
                        size_bytes=source_path.stat().st_size,
                    )
                )
                continue
            try:
                original_target = self._allocate_target_path(originals_dir, source_path.name)
                shutil.copy2(source_path, original_target)
                extracted = self.document_registry.extract(source_path)
                extracted_target = self._allocate_target_path(extracted_dir, f"{source_path.stem}.md")
                markdown = f"# {(extracted.suggested_title or source_path.stem).strip() or source_path.stem}\n\n{extracted.text.strip()}\n"
                extracted_target.write_text(markdown, encoding="utf-8")
            except Exception as exc:
                files.append(
                    self._record_for(
                        source_path,
                        extension,
                        status="failed",
                        size_bytes=source_path.stat().st_size,
                        error_message=str(exc),
                    )
                )
                continue
            imported_count += 1
            files.append(
                self._record_for(
                    original_target,
                    extension,
                    status="imported",
                    source_path=source_path,
                    stored_path=original_target,
                    size_bytes=original_target.stat().st_size,
                )
            )

        index_status = None
        if rebuild_index and imported_count > 0:
            index_status = self.rebuild_index()
        return KnowledgeImportResult(files=files, imported_count=imported_count, index_status=index_status)

    def rebuild_index(self) -> KnowledgeIndexStatus:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir = self.uploads_dir / "extracted"
        source_paths = sorted(candidate for candidate in extracted_dir.rglob("*") if candidate.is_file()) if extracted_dir.exists() else []
        summary = build_knowledge_index(
            knowledge_dir=self.knowledge_dir,
            index_path=self.index_path,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            source_paths=source_paths,
        )
        return KnowledgeIndexStatus(
            ready=self.index_path.exists(),
            index_path=str(summary["index_path"]),
            documents_loaded=int(summary["documents_loaded"]),
            chunks_created=int(summary["chunks_created"]),
            last_built_at=self._index_last_built_at(),
            embedding_provider="FakeEmbeddings",
            supported_extensions=self._supported_extensions(),
        )

    def list_files(self) -> list[KnowledgeFileRecord]:
        originals_dir = self.uploads_dir / "originals"
        if not originals_dir.exists():
            return []
        records: list[KnowledgeFileRecord] = []
        for path in sorted(candidate for candidate in originals_dir.rglob("*") if candidate.is_file()):
            records.append(
                self._record_for(
                    path,
                    path.suffix.lower(),
                    status="imported",
                    source_path=path,
                    stored_path=path,
                    size_bytes=path.stat().st_size,
                )
            )
        return records

    def get_status(self) -> KnowledgeIndexStatus:
        payload: dict[str, object] = {}
        if self.index_path.exists():
            try:
                raw_payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                raw_payload = {}
            if isinstance(raw_payload, dict):
                payload = raw_payload
        return KnowledgeIndexStatus(
            ready=self.index_path.exists(),
            index_path=str(self.index_path),
            documents_loaded=int(payload.get("documents_loaded", 0) or 0),
            chunks_created=int(payload.get("chunks_created", 0) or 0),
            last_built_at=self._index_last_built_at(),
            embedding_provider=str(payload.get("embedding_provider")) if payload.get("embedding_provider") else None,
            supported_extensions=self._supported_extensions(),
        )

    def _index_last_built_at(self) -> str | None:
        if not self.index_path.exists():
            return None
        return datetime.fromtimestamp(self.index_path.stat().st_mtime).isoformat()

    def _record_for(
        self,
        path: Path,
        extension: str,
        *,
        status: str,
        source_path: Path | None = None,
        stored_path: Path | None = None,
        size_bytes: int = 0,
        error_message: str | None = None,
    ) -> KnowledgeFileRecord:
        actual_source = source_path or path
        actual_stored = stored_path or Path("")
        return KnowledgeFileRecord(
            file_id=str((actual_stored or actual_source)).replace("\\", "/"),
            file_name=path.name,
            source_path=str(actual_source),
            stored_path=str(actual_stored),
            extension=extension,
            status=status,
            size_bytes=size_bytes,
            error_message=error_message,
        )

    def _allocate_target_path(self, directory: Path, filename: str) -> Path:
        candidate = directory / filename
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            next_candidate = directory / f"{stem}_{counter}{suffix}"
            if not next_candidate.exists():
                return next_candidate
            counter += 1

    def _supported_extensions(self) -> tuple[str, ...]:
        supported = getattr(self.document_registry, "supported_extensions", None)
        if callable(supported):
            return tuple(sorted(str(item) for item in supported()))
        return tuple(sorted(DocumentExtractorRegistry().supported_extensions()))
