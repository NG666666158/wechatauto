from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp"
TMP_ROOT.mkdir(exist_ok=True)


class ApiContractTests(unittest.TestCase):
    def test_build_api_contract_lists_frontend_critical_endpoints(self) -> None:
        from wechat_ai.server import create_app
        from scripts.export_api_contract import build_api_contract

        contract = build_api_contract(create_app().openapi())
        endpoint_keys = {(item["method"], item["path"]) for item in contract["endpoints"]}

        self.assertEqual(contract["contract_version"], "p4-baseline-v1")
        self.assertEqual(contract["base_path"], "/api/v1")
        self.assertIn(("GET", "/api/v1/dashboard/summary"), endpoint_keys)
        self.assertIn(("GET", "/api/v1/errors/catalog"), endpoint_keys)
        self.assertIn(("GET", "/api/v1/conversations"), endpoint_keys)
        self.assertIn(("POST", "/api/v1/conversations/{conversation_id}/send"), endpoint_keys)
        self.assertIn(("GET", "/api/v1/knowledge/status"), endpoint_keys)
        self.assertIn(("PATCH", "/api/v1/settings"), endpoint_keys)
        self.assertIn("/api/v1/conversations/{conversation_id}/send", contract["frontend_pages"]["messages"])

    def test_p4_first_batch_endpoints_use_typed_response_schemas(self) -> None:
        from wechat_ai.server import create_app
        from scripts.export_api_contract import build_api_contract

        contract = build_api_contract(create_app().openapi())
        schema_by_endpoint = {
            (item["method"], item["path"]): item["response_schema"]
            for item in contract["endpoints"]
        }

        expected_schema_fragments = {
            ("GET", "/api/v1/runtime/status"): "RuntimeStatus",
            ("POST", "/api/v1/runtime/start"): "RuntimeAction",
            ("POST", "/api/v1/runtime/stop"): "RuntimeAction",
            ("POST", "/api/v1/runtime/restart"): "RuntimeAction",
            ("GET", "/api/v1/dashboard/summary"): "DashboardSummary",
            ("GET", "/api/v1/settings"): "Settings",
            ("PATCH", "/api/v1/settings"): "Settings",
            ("GET", "/api/v1/logs/summary"): "LogsSummary",
            ("GET", "/api/v1/errors/catalog"): "ErrorCatalog",
        }

        for endpoint, schema_fragment in expected_schema_fragments.items():
            with self.subTest(endpoint=endpoint):
                response_schema = schema_by_endpoint[endpoint]
                self.assertIn(schema_fragment, response_schema)
                self.assertNotEqual(response_schema, "ApiResponse_dict_str__object__")

    def test_p4_second_batch_endpoints_use_typed_response_schemas(self) -> None:
        from wechat_ai.server import create_app
        from scripts.export_api_contract import build_api_contract

        contract = build_api_contract(create_app().openapi())
        schema_by_endpoint = {
            (item["method"], item["path"]): item["response_schema"]
            for item in contract["endpoints"]
        }

        expected_schema_fragments = {
            ("GET", "/api/v1/conversations"): "ConversationListItem",
            ("GET", "/api/v1/conversations/{conversation_id}"): "ConversationDetail",
            ("POST", "/api/v1/conversations/{conversation_id}/suggest"): "ReplySuggestion",
            ("POST", "/api/v1/conversations/{conversation_id}/send"): "SendReplyResult",
            ("GET", "/api/v1/customers"): "Customer",
            ("GET", "/api/v1/customers/{customer_id}"): "Customer",
            ("GET", "/api/v1/identity/drafts"): "IdentityDraft",
            ("GET", "/api/v1/identity/candidates"): "IdentityCandidate",
            ("GET", "/api/v1/identity/self/global"): "SelfIdentity",
            ("PATCH", "/api/v1/identity/self/global"): "SelfIdentity",
            ("GET", "/api/v1/knowledge/status"): "KnowledgeStatus",
            ("GET", "/api/v1/knowledge/search"): "KnowledgeSearchResult",
            ("POST", "/api/v1/knowledge/import"): "KnowledgeImportResult",
            ("POST", "/api/v1/knowledge/web-build"): "WebKnowledgeBuildResult",
            ("GET", "/api/v1/privacy/policy"): "PrivacyPolicy",
            ("PATCH", "/api/v1/privacy/policy"): "PrivacyPolicy",
            ("POST", "/api/v1/privacy/apply-retention"): "RetentionApplyResult",
            ("GET", "/api/v1/environment/wechat"): "WechatEnvironment",
            ("GET", "/api/v1/controls/conversations/{conversation_id}"): "ConversationControl",
            ("PATCH", "/api/v1/controls/conversations/{conversation_id}"): "ConversationControl",
        }

        for endpoint, schema_fragment in expected_schema_fragments.items():
            with self.subTest(endpoint=endpoint):
                response_schema = schema_by_endpoint[endpoint]
                self.assertIn(schema_fragment, response_schema)
                self.assertNotIn("dict_str__object", response_schema)

    def test_p4_request_schemas_are_typed_for_mutating_frontend_endpoints(self) -> None:
        from wechat_ai.server import create_app
        from scripts.export_api_contract import build_api_contract

        contract = build_api_contract(create_app().openapi())
        schema_by_endpoint = {
            (item["method"], item["path"]): item["request_schema"]
            for item in contract["endpoints"]
        }

        expected_request_schemas = {
            ("PATCH", "/api/v1/settings"): "SettingsPatchRequest",
            ("PATCH", "/api/v1/privacy/policy"): "PrivacyPolicyPatchRequest",
            ("PATCH", "/api/v1/controls/conversations/{conversation_id}"): "ConversationControlPatchRequest",
            ("PATCH", "/api/v1/identity/self/global"): "SelfIdentityPatchRequest",
            ("POST", "/api/v1/knowledge/import"): "KnowledgeImportRequest",
            ("POST", "/api/v1/knowledge/web-build"): "WebKnowledgeBuildRequest",
            ("POST", "/api/v1/conversations/{conversation_id}/suggest"): "ReplySuggestionRequest",
            ("POST", "/api/v1/conversations/{conversation_id}/send"): "SendReplyRequest",
        }

        for endpoint, request_schema in expected_request_schemas.items():
            with self.subTest(endpoint=endpoint):
                self.assertEqual(schema_by_endpoint[endpoint], request_schema)
                self.assertNotIn("dict_str__object", schema_by_endpoint[endpoint])

    def test_export_api_contract_writes_snapshot_files(self) -> None:
        output_dir = TMP_ROOT / "api_contract_tests" / str(uuid4())

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "export_api_contract.py"),
                "--output-dir",
                str(output_dir),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        stdout_contract = json.loads(result.stdout)
        baseline_path = output_dir / "api-contract.baseline.json"
        openapi_path = output_dir / "openapi.snapshot.json"

        self.assertEqual(stdout_contract["contract_version"], "p4-baseline-v1")
        self.assertTrue(baseline_path.exists())
        self.assertTrue(openapi_path.exists())
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
        self.assertEqual(baseline["endpoint_count"], stdout_contract["endpoint_count"])
        self.assertIn("/api/v1/runtime/status", openapi["paths"])


if __name__ == "__main__":
    unittest.main()
