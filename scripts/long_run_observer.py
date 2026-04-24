from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wechat_ai.logging_utils import RUNTIME_LOG_FILE, is_error_event, read_jsonl_events, sanitize_text  # noqa: E402


DEFAULT_OUTPUT = ROOT / "wechat_ai" / "data" / "logs" / "long_run_observer.jsonl"
ANOMALY_EVENT_TYPES = {
    "loop_error",
    "message_send_unconfirmed",
    "active_anchor_missed",
    "fallback_used",
    "send_skipped_stop_event",
}


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or "unknown").strip() or "unknown"


def _tail(events: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    return events[-limit:]


def _summarize_runtime_log(events: list[dict[str, Any]], *, recent_limit: int) -> dict[str, Any]:
    counts = Counter(_safe_event_type(event) for event in events)
    error_events = [event for event in events if is_error_event(event) or _safe_event_type(event) in ANOMALY_EVENT_TYPES]
    heartbeat_events = [event for event in events if _safe_event_type(event) == "heartbeat"]
    message_received = counts.get("message_received", 0)
    message_sent = counts.get("message_sent", 0)
    reply_ratio = round(message_sent / message_received, 4) if message_received else None
    return {
        "total_events": len(events),
        "event_counts": dict(sorted(counts.items())),
        "error_like_count": len(error_events),
        "first_event_time": events[0].get("timestamp") if events else None,
        "last_event_time": events[-1].get("timestamp") if events else None,
        "last_heartbeat_time": heartbeat_events[-1].get("timestamp") if heartbeat_events else None,
        "message_received_count": message_received,
        "message_sent_count": message_sent,
        "reply_ratio": reply_ratio,
        "recent_events": _tail(events, recent_limit),
        "recent_error_like_events": _tail(error_events, recent_limit),
    }


def _summarize_anomalies(events: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(_safe_event_type(event) for event in events)
    exception_counts = Counter(
        str(event.get("exception_type") or "").strip()
        for event in events
        if str(event.get("exception_type") or "").strip()
    )
    return {
        "loop_error_count": counts.get("loop_error", 0),
        "send_unconfirmed_count": counts.get("message_send_unconfirmed", 0),
        "active_anchor_missed_count": counts.get("active_anchor_missed", 0),
        "fallback_used_count": counts.get("fallback_used", 0),
        "stop_event_count": counts.get("stop_event_received", 0),
        "exception_counts": dict(sorted(exception_counts.items())),
    }


def _summarize_readiness(readiness_report: dict[str, Any] | None) -> dict[str, Any]:
    if not readiness_report:
        return {
            "available": False,
            "status_counts": {},
            "warn_check_ids": [],
            "error_check_ids": [],
        }
    checks = readiness_report.get("checks") if isinstance(readiness_report, dict) else []
    if not isinstance(checks, list):
        checks = []
    status_counts = Counter(str(item.get("status") or "unknown") for item in checks if isinstance(item, dict))
    warn_ids = [
        str(item.get("id"))
        for item in checks
        if isinstance(item, dict) and str(item.get("status") or "").lower() == "warn"
    ]
    error_ids = [
        str(item.get("id"))
        for item in checks
        if isinstance(item, dict) and str(item.get("status") or "").lower() in {"error", "fail"}
    ]
    return {
        "available": True,
        "status_counts": dict(sorted(status_counts.items())),
        "warn_check_ids": warn_ids,
        "error_check_ids": error_ids,
    }


def _summarize_window_probe(window_probe_report: dict[str, Any] | None) -> dict[str, Any]:
    probe = window_probe_report.get("probe") if isinstance(window_probe_report, dict) else None
    if not isinstance(probe, dict):
        return {
            "available": False,
            "ready": None,
            "status": "",
            "focus_recommendation": "",
        }
    return {
        "available": True,
        "ready": probe.get("ready"),
        "status": str(probe.get("status") or ""),
        "current_chat": str(probe.get("current_chat") or ""),
        "visible_message_count": int(probe.get("visible_message_count") or 0),
        "input_ready": probe.get("input_ready"),
        "window_minimized": probe.get("window_minimized"),
        "focus_recommendation": str(probe.get("focus_recommendation") or ""),
        "reason": str(probe.get("reason") or ""),
    }


def _diagnose(
    *,
    runtime_log: dict[str, Any],
    anomalies: dict[str, Any],
    readiness: dict[str, Any],
    window_probe: dict[str, Any],
) -> list[str]:
    diagnosis: list[str] = []
    if anomalies["loop_error_count"]:
        diagnosis.append("runtime_loop")
    if anomalies["send_unconfirmed_count"]:
        diagnosis.append("send_confirmation")
    if anomalies["active_anchor_missed_count"]:
        diagnosis.append("window_anchor")
    if anomalies["fallback_used_count"]:
        diagnosis.append("model_or_pipeline_fallback")
    if readiness.get("warn_check_ids") or readiness.get("error_check_ids"):
        diagnosis.append("environment_readiness")
    if window_probe.get("available") and not window_probe.get("ready"):
        diagnosis.append("window_probe")
    if runtime_log["total_events"] == 0:
        diagnosis.append("no_runtime_events")
    return diagnosis


def build_long_run_observation_report(
    *,
    log_file: Path | str = RUNTIME_LOG_FILE,
    readiness_report: dict[str, Any] | None = None,
    window_probe_report: dict[str, Any] | None = None,
    target_duration_minutes: int = 30,
    recent_limit: int = 20,
) -> dict[str, Any]:
    log_path = Path(log_file)
    events = read_jsonl_events(log_path)
    runtime_log = _summarize_runtime_log(events, recent_limit=recent_limit)
    anomalies = _summarize_anomalies(events)
    readiness = _summarize_readiness(readiness_report)
    window_probe = _summarize_window_probe(window_probe_report)
    diagnosis = _diagnose(
        runtime_log=runtime_log,
        anomalies=anomalies,
        readiness=readiness,
        window_probe=window_probe,
    )
    return {
        "script": "long_run_observer",
        "safe_read_only": True,
        "does_not_send_messages": True,
        "generated_at": _utc_now(),
        "target_duration_minutes": int(target_duration_minutes),
        "log_file": str(log_path),
        "runtime_log": runtime_log,
        "anomalies": anomalies,
        "readiness": readiness,
        "window_probe": window_probe,
        "diagnosis": diagnosis,
        "recommendations": build_recommendations(diagnosis),
    }


def build_recommendations(diagnosis: list[str]) -> list[str]:
    mapping = {
        "runtime_loop": "检查 loop_error 的 exception_type/exception_message，并确认微信窗口、模型接口和本地依赖是否稳定。",
        "send_confirmation": "检查发送后视觉确认是否能看到出站气泡；若频繁失败，优先检查输入框焦点和窗口遮挡。",
        "window_anchor": "active anchor missed 偏多时，优先检查滚动、切会话、窗口刷新和消息列表锚点策略。",
        "model_or_pipeline_fallback": "fallback_used 偏多时，检查模型 key、网络、RAG/身份上下文和回复 pipeline 异常。",
        "environment_readiness": "readiness 出现 warn/error 时，先处理微信登录态、讲述人残留、缩放、权限和 UI ready。",
        "window_probe": "window probe 未 ready 时，确认微信未最小化、当前会话可见、输入框可用。",
        "no_runtime_events": "没有 runtime event 时，确认监听脚本已经启动并使用同一个日志路径。",
    }
    return [mapping[item] for item in diagnosis if item in mapping]


def collect_readiness_report(skip: bool) -> dict[str, Any] | None:
    if skip:
        return None
    try:
        from scripts.check_wechat_real_run_readiness import build_readiness_report

        return build_readiness_report()
    except Exception as exc:
        return {"checks": [{"id": "readiness_exception", "status": "warn", "detail": f"{type(exc).__name__}: {exc}"}]}


def collect_window_probe_report(skip: bool) -> dict[str, Any] | None:
    if skip:
        return None
    try:
        from scripts.probe_wechat_window import build_probe_report

        return build_probe_report()
    except Exception as exc:
        return {"probe": {"ready": False, "status": "error", "reason": f"{type(exc).__name__}: {exc}"}}


def append_jsonl_report(output_path: Path, report: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")


def format_text(report: dict[str, Any]) -> str:
    runtime_log = report["runtime_log"]
    anomalies = report["anomalies"]
    lines = [
        "WeChat long-run observer",
        f"Safe read-only: {report['safe_read_only']}",
        f"Target duration: {report['target_duration_minutes']} minutes",
        f"Log file: {report['log_file']}",
        f"Total events: {runtime_log['total_events']}",
        f"Event counts: {json.dumps(runtime_log['event_counts'], ensure_ascii=False)}",
        f"Errors/anomalies: loop={anomalies['loop_error_count']} unconfirmed={anomalies['send_unconfirmed_count']} anchor_missed={anomalies['active_anchor_missed_count']} fallback={anomalies['fallback_used_count']}",
        f"Diagnosis: {', '.join(report['diagnosis']) or 'none'}",
    ]
    for recommendation in report["recommendations"]:
        lines.append(f"- {sanitize_text(recommendation)}")
    return "\n".join(lines)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only long-run observer for WeChat AI auto-reply.")
    parser.add_argument("--log-file", type=Path, default=RUNTIME_LOG_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-duration-minutes", type=int, default=30)
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--skip-readiness", action="store_true")
    parser.add_argument("--skip-window-probe", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    _configure_utf8_stdio()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_long_run_observation_report(
        log_file=args.log_file,
        readiness_report=collect_readiness_report(args.skip_readiness),
        window_probe_report=collect_window_probe_report(args.skip_window_probe),
        target_duration_minutes=args.target_duration_minutes,
        recent_limit=max(args.recent_limit, 0),
    )
    if not args.no_write:
        append_jsonl_report(args.output, report)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
