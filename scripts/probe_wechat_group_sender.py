from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyweixin import Navigator, Tools  # noqa: E402
from pyweixin.Uielements import Lists as _Lists  # noqa: E402
from pyweixin.Uielements import Texts as _Texts  # noqa: E402


Lists = _Lists() if callable(_Lists) else _Lists
Texts = _Texts() if callable(_Texts) else _Texts


def _safe_text(control: Any) -> str:
    getter = getattr(control, "window_text", None)
    if not callable(getter):
        return ""
    try:
        return str(getter()).strip()
    except Exception:
        return ""


def _runtime_id(item: Any) -> list[int] | str:
    element_info = getattr(item, "element_info", None)
    runtime_id = getattr(element_info, "runtime_id", "")
    if isinstance(runtime_id, tuple):
        return list(runtime_id)
    if isinstance(runtime_id, list):
        return runtime_id
    return str(runtime_id)


def build_group_sender_probe(limit: int = 20) -> dict[str, Any]:
    main_window = Navigator.open_weixin(is_maximize=False)
    try:
        try:
            current_chat = _safe_text(main_window.child_window(**Texts.CurrentChatText))
        except Exception:
            current_chat = ""

        try:
            is_group = bool(Tools.is_group_chat(main_window))
        except Exception:
            is_group = False

        messages: list[dict[str, Any]] = []
        if is_group:
            chat_list = main_window.child_window(**Lists.FriendChatList)
            items = chat_list.children(control_type="ListItem")[-limit:]
            for item in items:
                class_name = ""
                try:
                    class_name = str(item.class_name())
                except Exception:
                    pass
                if class_name != "mmui::ChatTextItemView":
                    continue
                try:
                    is_mine = bool(Tools.is_my_bubble(main_window, item))
                except Exception:
                    is_mine = False
                if is_mine:
                    continue
                try:
                    sender_name, text, message_type = Tools.parse_message_content(
                        ListItem=item,
                        friendtype="缇よ亰",
                    )
                    parse_status = "ok"
                    error = ""
                except Exception as exc:
                    sender_name = ""
                    text = _safe_text(item)
                    message_type = ""
                    parse_status = "error"
                    error = f"{type(exc).__name__}: {exc}"
                messages.append(
                    {
                        "sender_name": str(sender_name or "").strip(),
                        "text": str(text or "").strip(),
                        "message_type": str(message_type or "").strip(),
                        "runtime_id": _runtime_id(item),
                        "parse_status": parse_status,
                        "error": error,
                    }
                )

        return {
            "script": "probe_wechat_group_sender",
            "safe_read_only": True,
            "does_not_send_messages": True,
            "current_chat": current_chat,
            "is_group": is_group,
            "visible_incoming_text_count": len(messages),
            "messages": messages,
        }
    finally:
        close = getattr(main_window, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def format_text(report: dict[str, Any]) -> str:
    lines = [
        "WeChat group sender probe",
        f"Current chat: {report.get('current_chat') or '(unknown)'}",
        f"Is group: {report.get('is_group')}",
        f"Visible incoming text count: {report.get('visible_incoming_text_count')}",
    ]
    for message in report.get("messages", []):
        sender = message.get("sender_name") or "(unresolved)"
        text = message.get("text") or ""
        status = message.get("parse_status") or "unknown"
        lines.append(f"- [{status}] {sender}: {text}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only probe for WeChat group member sender parsing.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    report = build_group_sender_probe(limit=max(args.limit, 1))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
