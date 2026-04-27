from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_OUTPUT_DIR = ROOT / "docs" / "api-contract"
BASELINE_FILE_NAME = "api-contract.baseline.json"
OPENAPI_FILE_NAME = "openapi.snapshot.json"


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _operation_id(method: str, path: str) -> str:
    cleaned = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    return f"{method.lower()}_{cleaned or 'root'}"


def _schema_ref(schema: dict[str, Any] | None) -> str:
    if not schema:
        return ""
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    title = schema.get("title")
    if isinstance(title, str):
        return title
    if "items" in schema and isinstance(schema["items"], dict):
        item_ref = _schema_ref(schema["items"])
        return f"list[{item_ref}]" if item_ref else "list"
    return str(schema.get("type") or "")


def _request_schema(operation: dict[str, Any]) -> str:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return ""
    content = request_body.get("content")
    if not isinstance(content, dict):
        return ""
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return ""
    schema = json_content.get("schema")
    return _schema_ref(schema if isinstance(schema, dict) else None)


def _response_schema(operation: dict[str, Any]) -> str:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return ""
    ok_response = responses.get("200") or responses.get("201")
    if not isinstance(ok_response, dict):
        return ""
    content = ok_response.get("content")
    if not isinstance(content, dict):
        return ""
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return ""
    schema = json_content.get("schema")
    return _schema_ref(schema if isinstance(schema, dict) else None)


def build_api_contract(openapi: dict[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        paths = {}

    endpoints: list[dict[str, Any]] = []
    for path in sorted(paths):
        path_item = paths[path]
        if not isinstance(path_item, dict):
            continue
        for method in sorted(path_item):
            if method.lower() not in {"get", "post", "patch", "put", "delete"}:
                continue
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue
            endpoints.append(
                {
                    "id": _operation_id(method, path),
                    "method": method.upper(),
                    "path": path,
                    "tags": list(operation.get("tags") or []),
                    "summary": str(operation.get("summary") or ""),
                    "request_schema": _request_schema(operation),
                    "response_schema": _response_schema(operation),
                    "response_codes": sorted((operation.get("responses") or {}).keys()),
                }
            )

    schemas = openapi.get("components", {}).get("schemas", {})
    schema_names = sorted(schemas.keys()) if isinstance(schemas, dict) else []
    return {
        "contract_version": "p4-baseline-v1",
        "api_title": openapi.get("info", {}).get("title", ""),
        "api_version": openapi.get("info", {}).get("version", ""),
        "base_path": "/api/v1",
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "schema_count": len(schema_names),
        "schemas": schema_names,
        "frontend_pages": {
            "home": ["/api/v1/dashboard/summary", "/api/v1/runtime/status", "/api/v1/runtime/bootstrap-check", "/api/v1/runtime/bootstrap-start"],
            "messages": ["/api/v1/conversations", "/api/v1/conversations/{conversation_id}", "/api/v1/conversations/{conversation_id}/suggest", "/api/v1/conversations/{conversation_id}/send"],
            "customers": ["/api/v1/customers", "/api/v1/customers/{customer_id}", "/api/v1/identity/drafts", "/api/v1/identity/candidates"],
            "knowledge": ["/api/v1/knowledge/status", "/api/v1/knowledge/search", "/api/v1/knowledge/import", "/api/v1/knowledge/web-build"],
            "settings": ["/api/v1/settings", "/api/v1/privacy/policy", "/api/v1/environment/wechat", "/api/v1/controls/conversations/{conversation_id}", "/api/v1/errors/catalog"],
        },
    }


def export_api_contract(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    from wechat_ai.server import create_app

    app = create_app()
    openapi = app.openapi()
    contract = build_api_contract(openapi)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OPENAPI_FILE_NAME).write_text(
        _stable_json(openapi),
        encoding="utf-8",
    )
    (output_dir / BASELINE_FILE_NAME).write_text(
        _stable_json(contract),
        encoding="utf-8",
    )
    return contract


def assert_api_contract_snapshots_current(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    from wechat_ai.server import create_app

    openapi = create_app().openapi()
    contract = build_api_contract(openapi)
    expected_files = {
        BASELINE_FILE_NAME: _stable_json(contract),
        OPENAPI_FILE_NAME: _stable_json(openapi),
    }
    mismatches: list[str] = []
    for file_name, expected_text in expected_files.items():
        snapshot_path = output_dir / file_name
        if not snapshot_path.exists():
            mismatches.append(f"{file_name}: missing")
            continue
        actual_text = snapshot_path.read_text(encoding="utf-8")
        if actual_text != expected_text:
            mismatches.append(f"{file_name}: stale")
    if mismatches:
        detail = ", ".join(mismatches)
        raise AssertionError(
            "API contract snapshots are not current "
            f"({detail}). Run: py -3 scripts\\export_api_contract.py --output-dir docs\\api-contract --format json"
        )


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def format_contract_markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# API Contract Baseline",
        "",
        f"- Contract version: `{contract['contract_version']}`",
        f"- API: `{contract['api_title']}` `{contract['api_version']}`",
        f"- Base path: `{contract['base_path']}`",
        f"- Endpoint count: `{contract['endpoint_count']}`",
        f"- Schema count: `{contract['schema_count']}`",
        "",
        "## Endpoints",
        "",
        "| Method | Path | Request | Response |",
        "| --- | --- | --- | --- |",
    ]
    for endpoint in contract["endpoints"]:
        lines.append(
            f"| `{endpoint['method']}` | `{endpoint['path']}` | `{endpoint['request_schema'] or '-'}` | `{endpoint['response_schema'] or '-'}` |"
        )
    lines.extend(["", "## Frontend Pages", ""])
    for page, paths in contract["frontend_pages"].items():
        lines.append(f"- `{page}`: " + ", ".join(f"`{path}`" for path in paths))
    return "\n".join(lines) + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the local FastAPI OpenAPI snapshot and frontend API contract baseline.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--check", action="store_true", help="Verify committed snapshots are current without writing files.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    _configure_utf8_stdio()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        try:
            assert_api_contract_snapshots_current(args.output_dir)
        except AssertionError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("API contract snapshots are current")
        return 0
    contract = export_api_contract(args.output_dir)
    if args.format == "markdown":
        print(format_contract_markdown(contract))
    else:
        print(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
