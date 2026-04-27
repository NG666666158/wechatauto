from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_OUTPUT_DIR = ROOT / "docs" / "api-contract" / "fixtures"


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def build_api_fixtures() -> dict[str, dict[str, object]]:
    from wechat_ai.server.core import error_catalog, success_response
    from wechat_ai.server.schemas import (
        ConversationControlData,
        ConversationDetailData,
        ConversationListItemData,
        CustomerData,
        DashboardSummaryData,
        IdentityCandidateData,
        IdentityDraftData,
        KnowledgeFileImportData,
        KnowledgeImportResultData,
        KnowledgeSearchResultData,
        KnowledgeStatusData,
        LogsSummaryData,
        PrivacyPolicyData,
        ReplySuggestionData,
        RuntimeStatusData,
        SelfIdentityData,
        SendReplyResultData,
        SettingsData,
        WebKnowledgeBuildResultData,
        WechatEnvironmentData,
    )
    from wechat_ai.server.schemas.runtime import AppStatusData, DaemonStatusData

    dashboard = DashboardSummaryData(
        app=AppStatusData(
            wechat_status="connected",
            daemon_state="running",
            auto_reply_enabled=True,
            today_received=128,
            today_replied=256,
            pending_count=12,
            knowledge_index_ready=True,
            last_heartbeat="2026-04-25T09:45:32+08:00",
        ),
        runtime=RuntimeStatusData(
            state="running",
            mode="global",
            running=True,
            daemon=DaemonStatusData(
                state="running",
                pid=4321,
                run_silently=True,
                last_heartbeat="2026-04-25T09:45:32+08:00",
                last_started_at="2026-04-25T08:58:00+08:00",
                today_received=128,
                today_replied=256,
            ),
            app=AppStatusData(
                wechat_status="connected",
                daemon_state="running",
                auto_reply_enabled=True,
                today_received=128,
                today_replied=256,
                pending_count=12,
                knowledge_index_ready=True,
                last_heartbeat="2026-04-25T09:45:32+08:00",
            ),
        ),
        knowledge=KnowledgeStatusData(
            ready=True,
            index_path="data/knowledge/index.faiss",
            documents_loaded=18,
            chunks_created=426,
            last_built_at="2026-04-24T22:15:00+08:00",
            embedding_provider="local",
            supported_extensions=[".pdf", ".docx", ".txt", ".md", ".png", ".jpg"],
        ),
    )
    conversations = [
        ConversationListItemData(
            conversation_id="friend:zhang",
            title="张先生",
            is_group=False,
            latest_message="请问你们的产品支持试用吗？",
            unread_count=1,
            updated_at="2026-04-25T09:41:00+08:00",
        ),
        ConversationListItemData(
            conversation_id="friend:li",
            title="李女士",
            is_group=False,
            latest_message="价格方案能再详细一点吗？",
            unread_count=2,
            updated_at="2026-04-25T09:39:00+08:00",
        ),
    ]
    conversation_detail = ConversationDetailData(
        conversation=conversations[0],
        messages=[
            {
                "message_id": "msg_001",
                "conversation_id": "friend:zhang",
                "sender": "张先生",
                "text": "请问你们的产品支持试用吗？",
                "direction": "incoming",
                "sent_at": "2026-04-25T09:41:00+08:00",
            },
            {
                "message_id": "msg_002",
                "conversation_id": "friend:zhang",
                "sender": "assistant",
                "text": "支持 7 天试用，我可以先给你发申请方式。",
                "direction": "outgoing",
                "sent_at": "2026-04-25T09:41:10+08:00",
            },
        ],
        control=ConversationControlData(conversation_id="friend:zhang"),
    )
    customers = [
        CustomerData(
            customer_id="user_001",
            display_name="张先生",
            status="intent",
            tags=["意向客户", "线上咨询"],
            remark="关注产品功能与试用政策，预计本周安排演示。",
            last_contact_at="2026-04-25T09:41:00+08:00",
        ),
        CustomerData(
            customer_id="user_002",
            display_name="李女士",
            status="follow_up",
            tags=["高意向"],
            remark="需要优惠方案和交付周期说明。",
            last_contact_at="2026-04-25T09:39:00+08:00",
        ),
    ]
    settings = SettingsData(
        auto_reply_enabled=True,
        reply_style="专业友好",
        new_customer_auto_create=True,
        sensitive_message_review=True,
        knowledge_chunk_size=1000,
        knowledge_chunk_overlap=200,
        run_silently=True,
        esc_action="pause",
        request_timeout_seconds=30.0,
        retry_attempts=2,
        real_send_enabled=False,
    )

    fixtures = {
        "home/dashboard.summary.json": success_response(dashboard.model_dump(mode="json"), trace_id="fixture-home-dashboard"),
        "home/runtime.status.json": success_response(dashboard.runtime.model_dump(mode="json"), trace_id="fixture-home-runtime"),
        "home/logs.summary.json": success_response(
            LogsSummaryData(
                recent_count=24,
                recent_error_count=2,
                last_event_time="2026-04-25T09:45:00+08:00",
            ).model_dump(mode="json"),
            trace_id="fixture-home-logs-summary",
        ),
        "messages/conversations.list.json": success_response(
            [item.model_dump(mode="json") for item in conversations],
            trace_id="fixture-messages-list",
        ),
        "messages/conversation.detail.json": success_response(
            conversation_detail.model_dump(mode="json"),
            trace_id="fixture-messages-detail",
        ),
        "messages/reply.suggestion.json": success_response(
            ReplySuggestionData(
                conversation_id="friend:zhang",
                input_text="请问你们的产品支持试用吗？",
                suggestion="支持 7 天试用，我可以把申请流程和注意事项一起发你。",
                status="ready",
            ).model_dump(mode="json"),
            trace_id="fixture-messages-suggest",
        ),
        "messages/send.reply.blocked.json": success_response(
            SendReplyResultData(
                status="blocked",
                allowed=False,
                conversation_id="friend:zhang",
                text="",
                reason_code="EMPTY_TEXT",
                reason="回复内容不能为空。",
            ).model_dump(mode="json"),
            trace_id="fixture-messages-send-blocked",
        ),
        "messages/send.reply.sent.json": success_response(
            SendReplyResultData(
                status="sent",
                allowed=True,
                conversation_id="friend:zhang",
                text="支持 7 天试用，我可以先给你发申请方式。",
                reason_code="",
                reason="",
            ).model_dump(mode="json"),
            trace_id="fixture-messages-send-sent",
        ),
        "customers/customers.list.json": success_response(
            [item.model_dump(mode="json") for item in customers],
            trace_id="fixture-customers-list",
        ),
        "customers/customer.detail.json": success_response(
            customers[0].model_dump(mode="json"),
            trace_id="fixture-customers-detail",
        ),
        "customers/identity.drafts.json": success_response(
            [IdentityDraftData(draft_user_id="draft_user_001").model_dump(mode="json")],
            trace_id="fixture-customers-identity-drafts",
        ),
        "customers/identity.candidates.json": success_response(
            [IdentityCandidateData(candidate_id="candidate_001").model_dump(mode="json")],
            trace_id="fixture-customers-identity-candidates",
        ),
        "customers/identity.self.json": success_response(
            SelfIdentityData(
                display_name="碱水",
                identity_facts=["我是产品顾问", "面对老师或家人时会切换相应身份事实"],
            ).model_dump(mode="json"),
            trace_id="fixture-customers-identity-self",
        ),
        "knowledge/knowledge.status.json": success_response(
            dashboard.knowledge.model_dump(mode="json"),
            trace_id="fixture-knowledge-status",
        ),
        "knowledge/knowledge.search.json": success_response(
            [
                KnowledgeSearchResultData(
                    chunk_id="chunk_001",
                    text="产品支持 7 天试用，需要提交公司名称和联系人。",
                    score=0.93,
                ).model_dump(mode="json"),
                KnowledgeSearchResultData(
                    chunk_id="chunk_002",
                    text="价格方案支持基础版和专业版两档。",
                    score=0.87,
                ).model_dump(mode="json"),
            ],
            trace_id="fixture-knowledge-search",
        ),
        "knowledge/knowledge.import.json": success_response(
            KnowledgeImportResultData(
                files=[
                    KnowledgeFileImportData(file_name="产品手册.pdf", status="imported"),
                    KnowledgeFileImportData(file_name="FAQ.docx", status="imported"),
                ],
                index_rebuilt=True,
            ).model_dump(mode="json"),
            trace_id="fixture-knowledge-import",
        ),
        "knowledge/knowledge.web-build.json": success_response(
            WebKnowledgeBuildResultData(
                documents=["产品手册.pdf", "行业资料合集.docx"],
                search_limit=5,
                status="built",
            ).model_dump(mode="json"),
            trace_id="fixture-knowledge-web-build",
        ),
        "settings/settings.get.json": success_response(settings.model_dump(mode="json"), trace_id="fixture-settings-get"),
        "settings/privacy.policy.json": success_response(
            PrivacyPolicyData(
                redact_sensitive_logs=True,
                log_retention_days=14,
                memory_retention_days=90,
                max_recent_log_events=100,
            ).model_dump(mode="json"),
            trace_id="fixture-settings-privacy",
        ),
        "settings/environment.wechat.json": success_response(
            WechatEnvironmentData(
                wechat_running=True,
                narrator_required=False,
                ui_ready=True,
            ).model_dump(mode="json"),
            trace_id="fixture-settings-environment",
        ),
        "settings/controls.conversation.json": success_response(
            ConversationControlData(
                conversation_id="friend:zhang",
                human_takeover=False,
                paused=False,
                whitelisted=False,
                blacklisted=False,
            ).model_dump(mode="json"),
            trace_id="fixture-settings-control",
        ),
        "settings/errors.catalog.json": success_response(error_catalog(), trace_id="fixture-settings-errors"),
        "settings/logs.recent.json": success_response(
            [
                {
                    "timestamp": "2026-04-25T09:40:00+08:00",
                    "event_type": "runtime.status",
                    "trace_id": "trace-runtime-ok",
                    "message": "daemon running",
                },
                {
                    "timestamp": "2026-04-25T09:41:10+08:00",
                    "event_type": "message.sent",
                    "trace_id": "trace-send-001",
                    "conversation_id": "friend:zhang",
                    "message": "reply sent",
                },
            ],
            trace_id="fixture-settings-logs-recent",
        ),
    }
    return fixtures


def export_api_fixtures(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    fixtures = build_api_fixtures()
    written_files: list[str] = []
    for relative_path, payload in fixtures.items():
        target = output_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_stable_json(payload), encoding="utf-8")
        written_files.append(relative_path)
    written_files.sort()
    return {
        "fixture_count": len(written_files),
        "fixtures": written_files,
    }


def assert_api_fixtures_current(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    fixtures = build_api_fixtures()
    mismatches: list[str] = []
    for relative_path, payload in fixtures.items():
        target = output_dir / relative_path
        expected_text = _stable_json(payload)
        if not target.exists():
            mismatches.append(f"{relative_path}: missing")
            continue
        if target.read_text(encoding="utf-8") != expected_text:
            mismatches.append(f"{relative_path}: stale")
    if mismatches:
        detail = ", ".join(mismatches)
        raise AssertionError(
            "API fixtures are not current "
            f"({detail}). Run: py -3 scripts\\export_api_fixtures.py --output-dir docs\\api-contract\\fixtures"
        )


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export frontend-ready API fixtures from the current backend contract.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="Verify committed fixtures are current without writing files.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    _configure_utf8_stdio()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        try:
            assert_api_fixtures_current(args.output_dir)
        except AssertionError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("API fixtures are current")
        return 0
    manifest = export_api_fixtures(args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
