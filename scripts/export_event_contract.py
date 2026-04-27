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
EVENT_CONTRACT_FILE_NAME = "event-contract.json"


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def build_event_contract() -> dict[str, object]:
    from wechat_ai.server.schemas import EventContractData, EventFieldSpecData, EventTypeContractData

    envelope = {
        "id": EventFieldSpecData(type="string", description="事件唯一 ID，用于前端去重和恢复。"),
        "type": EventFieldSpecData(type="string", description="事件类型。"),
        "timestamp": EventFieldSpecData(type="string", description="ISO 8601 时间戳。"),
        "data": EventFieldSpecData(type="object", description="事件负载。"),
        "trace_id": EventFieldSpecData(type="string", description="关联 API / runtime trace id。"),
    }
    events = [
        EventTypeContractData(
            type="runtime.status",
            description="守护进程状态变化、心跳、退避重试等运行时状态更新。",
            payload_schema={
                "state": EventFieldSpecData(type="string", description="running/stopped/backoff"),
                "mode": EventFieldSpecData(type="string", description="运行模式。"),
                "running": EventFieldSpecData(type="boolean", description="当前是否在运行。"),
                "last_heartbeat": EventFieldSpecData(type="string", required=False, description="最近心跳时间。"),
            },
            sample={
                "state": "running",
                "mode": "global",
                "running": True,
                "last_heartbeat": "2026-04-25T10:00:00+08:00",
            },
        ),
        EventTypeContractData(
            type="message.received",
            description="监听到新的微信消息。",
            payload_schema={
                "conversation_id": EventFieldSpecData(type="string", description="会话标识。"),
                "sender": EventFieldSpecData(type="string", description="发送者名称或群成员名。"),
                "text": EventFieldSpecData(type="string", description="消息文本。"),
                "is_group": EventFieldSpecData(type="boolean", description="是否群聊。"),
            },
            sample={
                "conversation_id": "friend:zhang",
                "sender": "张先生",
                "text": "请问你们的产品支持试用吗？",
                "is_group": False,
            },
        ),
        EventTypeContractData(
            type="message.sent",
            description="自动回复发送结果事件。",
            payload_schema={
                "conversation_id": EventFieldSpecData(type="string", description="会话标识。"),
                "status": EventFieldSpecData(type="string", description="sent/unconfirmed/failed/blocked"),
                "text": EventFieldSpecData(type="string", description="回复文本。"),
                "reason_code": EventFieldSpecData(type="string", required=False, description="业务阻断或失败原因码。"),
            },
            sample={
                "conversation_id": "friend:zhang",
                "status": "sent",
                "text": "支持 7 天试用，我可以先把申请方式发你。",
                "reason_code": "",
            },
        ),
        EventTypeContractData(
            type="knowledge.progress",
            description="知识库导入、切分、建索引、联网扩库的阶段性进度。",
            payload_schema={
                "stage": EventFieldSpecData(type="string", description="extract/chunk/embed/index/search"),
                "current": EventFieldSpecData(type="integer", description="当前进度值。"),
                "total": EventFieldSpecData(type="integer", description="总进度值。"),
                "message": EventFieldSpecData(type="string", required=False, description="阶段说明。"),
            },
            sample={
                "stage": "index",
                "current": 18,
                "total": 18,
                "message": "知识库索引构建完成",
            },
        ),
        EventTypeContractData(
            type="log.event",
            description="面向前端日志面板的普通日志事件。",
            payload_schema={
                "level": EventFieldSpecData(type="string", description="info/warn/error"),
                "event_type": EventFieldSpecData(type="string", description="运行时事件类型。"),
                "message": EventFieldSpecData(type="string", description="可展示日志文案。"),
            },
            sample={
                "level": "info",
                "event_type": "runtime.status",
                "message": "daemon running",
            },
        ),
        EventTypeContractData(
            type="error",
            description="前端需要单独感知的异常事件。",
            payload_schema={
                "code": EventFieldSpecData(type="string", description="错误码。"),
                "message": EventFieldSpecData(type="string", description="错误说明。"),
                "detail": EventFieldSpecData(type="object", required=False, description="附加细节。"),
            },
            sample={
                "code": "WECHAT_WINDOW_NOT_FOUND",
                "message": "未发现可操作的微信窗口",
                "detail": {"ui_ready": False},
            },
        ),
    ]
    return EventContractData(envelope=envelope, events=events).model_dump(mode="json")


def export_event_contract(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    contract = build_event_contract()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / EVENT_CONTRACT_FILE_NAME).write_text(_stable_json(contract), encoding="utf-8")
    return contract


def assert_event_contract_snapshot_current(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    expected_text = _stable_json(build_event_contract())
    snapshot_path = output_dir / EVENT_CONTRACT_FILE_NAME
    if not snapshot_path.exists():
        raise AssertionError(
            "Event contract snapshot is not current "
            f"({EVENT_CONTRACT_FILE_NAME}: missing). Run: py -3 scripts\\export_event_contract.py --output-dir docs\\api-contract"
        )
    actual_text = snapshot_path.read_text(encoding="utf-8")
    if actual_text != expected_text:
        raise AssertionError(
            "Event contract snapshot is not current "
            f"({EVENT_CONTRACT_FILE_NAME}: stale). Run: py -3 scripts\\export_event_contract.py --output-dir docs\\api-contract"
        )


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the reserved front-end event contract snapshot.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="Verify committed event contract is current without writing files.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    _configure_utf8_stdio()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        try:
            assert_event_contract_snapshot_current(args.output_dir)
        except AssertionError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("Event contract snapshot is current")
        return 0
    contract = export_event_contract(args.output_dir)
    print(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
