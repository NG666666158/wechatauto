from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from wechat_ai import paths
from wechat_ai.app.knowledge_importer import KnowledgeImporter
from wechat_ai.rag.document_extractors import DocumentExtractorRegistry


SearchClient = Callable[[str, int], list[dict[str, str]]]
FetchClient = Callable[[str], dict[str, str]]


@dataclass(frozen=True)
class SeedDocument:
    path: Path
    title: str
    text: str


class WebKnowledgeBuilder:
    def __init__(
        self,
        *,
        knowledge_dir: Path | None = None,
        knowledge_importer: KnowledgeImporter | None = None,
        document_registry: DocumentExtractorRegistry | None = None,
        search_client: SearchClient | None = None,
        fetch_client: FetchClient | None = None,
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir or paths.KNOWLEDGE_DIR)
        self.knowledge_importer = knowledge_importer or KnowledgeImporter(knowledge_dir=self.knowledge_dir)
        self.document_registry = document_registry or DocumentExtractorRegistry()
        self.search_client = search_client or duckduckgo_search
        self.fetch_client = fetch_client or fetch_web_document

    def build_from_documents(
        self,
        file_paths: Iterable[Path | str],
        *,
        search_limit: int = 5,
    ) -> dict[str, object]:
        seeds = self._load_seed_documents(file_paths)
        queries = self._build_queries(seeds)
        candidates: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for query in queries:
            for result in self.search_client(query, search_limit):
                url = _normalize_candidate_url(str(result.get("url", "")).strip())
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(
                    {
                        "query": query,
                        "title": str(result.get("title", "")).strip(),
                        "url": url,
                        "snippet": str(result.get("snippet", "")).strip(),
                    }
                )
                if len(candidates) >= search_limit:
                    break
            if len(candidates) >= search_limit:
                break

        fetched_paths = self._fetch_and_store(candidates)
        import_result = self.knowledge_importer.import_files(fetched_paths, rebuild_index=bool(fetched_paths))
        index_status = import_result.index_status or self.knowledge_importer.get_status()

        return {
            "seed_documents": len(seeds),
            "queries": queries,
            "candidate_count": len(candidates),
            "fetched_count": len(fetched_paths),
            "imported_count": import_result.imported_count,
            "fetched_files": [str(path) for path in fetched_paths],
            "index_status": {
                "ready": bool(index_status.ready),
                "index_path": index_status.index_path,
                "documents_loaded": int(index_status.documents_loaded),
                "chunks_created": int(index_status.chunks_created),
                "supported_extensions": list(index_status.supported_extensions),
            },
        }

    def _load_seed_documents(self, file_paths: Iterable[Path | str]) -> list[SeedDocument]:
        seeds: list[SeedDocument] = []
        for raw_path in file_paths:
            extracted = self.document_registry.extract(raw_path)
            text = extracted.text.strip()
            if not text:
                continue
            path = Path(raw_path)
            seeds.append(
                SeedDocument(
                    path=path,
                    title=(extracted.suggested_title or path.stem).strip() or path.stem,
                    text=text,
                )
            )
        return seeds

    def _build_queries(self, seeds: list[SeedDocument]) -> list[str]:
        queries: list[str] = []
        for seed in seeds:
            keywords = _extract_keywords(seed.text)
            base = " ".join([seed.title, *keywords[:4]]).strip()
            if base:
                queries.append(f"{base} 最新 资料")
                queries.append(f"{base} best practices 2026")
        deduped: list[str] = []
        seen: set[str] = set()
        for query in queries:
            normalized = query.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(normalized)
        return deduped[:4]

    def _fetch_and_store(self, candidates: list[dict[str, str]]) -> list[Path]:
        fetched_dir = self.knowledge_dir / "web" / "fetched"
        fetched_dir.mkdir(parents=True, exist_ok=True)
        stored_paths: list[Path] = []
        for candidate in candidates:
            fetched = self.fetch_client(candidate["url"])
            content = str(fetched.get("content", "")).strip()
            if not content:
                continue
            title = str(fetched.get("title", "")).strip() or candidate["title"] or "网页资料"
            target_path = fetched_dir / f"{_slugify(title)}-{_short_hash(candidate['url'])}.md"
            markdown = (
                f"# {title}\n\n"
                f"来源链接: {candidate['url']}\n\n"
                f"搜索摘要: {candidate['snippet']}\n\n"
                f"{content}\n"
            )
            target_path.write_text(markdown, encoding="utf-8")
            stored_paths.append(target_path)
        return stored_paths


def duckduckgo_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    request = Request(
        url=f"https://duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", errors="ignore")
    parser = _DuckDuckGoHtmlParser(limit=limit)
    parser.feed(html)
    return parser.results


def fetch_web_document(url: str) -> dict[str, str]:
    request = Request(url=url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = _strip_html(title_match.group(1)) if title_match else urlparse(url).netloc or "网页资料"
    text = _strip_html(html)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "title": title, "content": text[:12000]}


class _DuckDuckGoHtmlParser(HTMLParser):
    def __init__(self, *, limit: int) -> None:
        super().__init__()
        self.limit = limit
        self.results: list[dict[str, str]] = []
        self._current_href = ""
        self._current_title: list[str] = []
        self._capture_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "") or ""
        if tag == "a" and "result__a" in classes:
            self._capture_title = True
            self._current_href = attrs_dict.get("href", "") or ""
            self._current_title = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            title = "".join(self._current_title).strip()
            if title and self._current_href and len(self.results) < self.limit:
                self.results.append(
                    {
                        "title": title,
                        "url": _normalize_candidate_url(self._current_href),
                        "snippet": "",
                    }
                )
            self._capture_title = False
            self._current_href = ""
            self._current_title = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._current_title.append(data)


def _normalize_candidate_url(raw_url: str) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return ""
    if value.startswith("//"):
        value = f"https:{value}"
    parsed = urlparse(value)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return value


def _extract_keywords(text: str) -> list[str]:
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    latin_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,20}", text)
    terms = chinese_terms + [term.lower() for term in latin_terms]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term not in seen:
            seen.add(term)
            deduped.append(term)
    return deduped[:12]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip().lower(), flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "web-doc"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return json.loads(json.dumps(text, ensure_ascii=False))
