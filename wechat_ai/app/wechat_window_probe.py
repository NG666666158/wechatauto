from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(slots=True)
class VisibleMessage:
    text: str
    runtime_id: object | None = None
    is_mine: bool | None = None


@dataclass(slots=True)
class WeChatUIProbeResult:
    ready: bool
    status: str
    reason: str
    current_chat: str = ""
    visible_message_count: int = 0
    latest_visible_text: str = ""
    input_ready: bool = False
    window_ready: bool = False
    window_minimized: bool = False
    current_chat_ready: bool = False
    chat_list_ready: bool = False
    focus_recommendation: str = ""
    messages: list[VisibleMessage] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["messages"] = [asdict(item) for item in self.messages or []]
        return payload


class WeChatWindowProbe:
    """Read-only pyweixin UI probe used before/after real WeChat operations."""

    def __init__(
        self,
        *,
        navigator: Any | None = None,
        tools: Any | None = None,
        lists: Any | None = None,
        edits: Any | None = None,
        texts: Any | None = None,
    ) -> None:
        self.navigator = navigator
        self.tools = tools
        self.lists = lists
        self.edits = edits
        self.texts = texts

    @classmethod
    def from_pyweixin(cls) -> "WeChatWindowProbe":
        from pyweixin import Navigator, Tools
        from pyweixin.Uielements import Edits as RawEdits
        from pyweixin.Uielements import Lists as RawLists
        from pyweixin.Uielements import Texts as RawTexts

        edits = RawEdits() if callable(RawEdits) else RawEdits
        lists = RawLists() if callable(RawLists) else RawLists
        texts = RawTexts() if callable(RawTexts) else RawTexts
        return cls(navigator=Navigator, tools=Tools, lists=lists, edits=edits, texts=texts)

    def probe_ui_ready(self, *, recent_limit: int = 20) -> WeChatUIProbeResult:
        try:
            main_window = self._open_main_window()
            window_ready = _safe_exists(main_window)
            window_minimized = _safe_is_minimized(main_window)
            current_chat_element = self._child_window(main_window, self.texts.CurrentChatText)
            current_chat = _safe_window_text(current_chat_element)
            chat_list = self._child_window(main_window, self.lists.FriendChatList)
            input_edit = self._child_window(main_window, self.edits.InputEdit)
            input_ready = _safe_exists(input_edit) and _safe_is_enabled(input_edit)
            messages = self.collect_visible_messages(main_window=main_window, chat_list=chat_list, limit=recent_limit)
        except Exception as exc:
            return WeChatUIProbeResult(
                ready=False,
                status="error",
                reason=f"{type(exc).__name__}: {exc}",
                messages=[],
            )

        latest_text = messages[-1].text if messages else ""
        current_chat_ready = bool(current_chat)
        chat_list_ready = bool(messages)
        ready = window_ready and not window_minimized and current_chat_ready and chat_list_ready and input_ready
        focus_recommendation = _build_focus_recommendation(
            window_ready=window_ready,
            window_minimized=window_minimized,
            current_chat_ready=current_chat_ready,
            chat_list_ready=chat_list_ready,
            input_ready=input_ready,
        )
        return WeChatUIProbeResult(
            ready=ready,
            status="ok" if ready else "warn",
            reason="" if ready else "微信窗口可见，但当前聊天、消息列表或输入框信号不完整。",
            current_chat=current_chat,
            visible_message_count=len(messages),
            latest_visible_text=latest_text,
            input_ready=input_ready,
            window_ready=window_ready,
            window_minimized=window_minimized,
            current_chat_ready=current_chat_ready,
            chat_list_ready=chat_list_ready,
            focus_recommendation=focus_recommendation,
            messages=messages,
        )

    def collect_visible_messages(
        self,
        *,
        main_window: Any | None = None,
        chat_list: Any | None = None,
        limit: int = 20,
    ) -> list[VisibleMessage]:
        if main_window is None:
            main_window = self._open_main_window()
        if chat_list is None:
            chat_list = self._child_window(main_window, self.lists.FriendChatList)
        items = _list_items(chat_list)
        messages: list[VisibleMessage] = []
        for item in items[-max(int(limit), 1) :]:
            text = _safe_window_text(item)
            if not text:
                continue
            messages.append(
                VisibleMessage(
                    text=text,
                    runtime_id=_runtime_id(item),
                    is_mine=self._safe_is_my_bubble(main_window, item),
                )
            )
        return messages

    def _open_main_window(self) -> Any:
        if self.navigator is None:
            raise RuntimeError("navigator is not configured")
        return self.navigator.open_weixin(is_maximize=False)

    def _child_window(self, main_window: Any, spec: Mapping[str, object]) -> Any:
        if not hasattr(main_window, "child_window"):
            raise RuntimeError("微信主窗口不可读")
        return main_window.child_window(**dict(spec))

    def _safe_is_my_bubble(self, main_window: Any, item: Any) -> bool | None:
        checker = getattr(self.tools, "is_my_bubble", None)
        if not callable(checker):
            return None
        try:
            return bool(checker(main_window, item))
        except Exception:
            return None


class PyWeixinVisualSendConfirmer:
    def __init__(
        self,
        *,
        probe: WeChatWindowProbe | None = None,
        timeout_seconds: float = 3.0,
        poll_interval_seconds: float = 0.25,
        recent_limit: int = 12,
    ) -> None:
        self.probe = probe or WeChatWindowProbe.from_pyweixin()
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.recent_limit = recent_limit

    def confirm_sent(
        self,
        *,
        conversation_id: str,
        text: str,
        is_group: bool = False,
        send_result: dict[str, object] | None = None,
    ) -> bool:
        del conversation_id, is_group, send_result
        target = _normalize_text(text)
        if not target:
            return False
        deadline = time.time() + max(self.timeout_seconds, 0.0)
        while True:
            messages = self.probe.collect_visible_messages(limit=self.recent_limit)
            if _has_matching_visible_message(messages, target):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(max(self.poll_interval_seconds, 0.01))


def probe_wechat_ui_ready() -> dict[str, object]:
    return WeChatWindowProbe.from_pyweixin().probe_ui_ready().to_dict()


def _has_matching_visible_message(messages: Sequence[VisibleMessage], target: str) -> bool:
    normalized_target = _normalize_text(target)
    if not normalized_target:
        return False
    outgoing_matches = [
        item for item in messages if item.is_mine is True and _normalize_text(item.text) == normalized_target
    ]
    if outgoing_matches:
        return True
    return any(item.is_mine is None and _normalize_text(item.text) == normalized_target for item in messages[-3:])


def _list_items(chat_list: Any) -> list[Any]:
    children = getattr(chat_list, "children", None)
    if not callable(children):
        return []
    try:
        return list(children(control_type="ListItem"))
    except TypeError:
        return list(children())


def _runtime_id(item: Any) -> object | None:
    element_info = getattr(item, "element_info", None)
    return getattr(element_info, "runtime_id", None)


def _safe_exists(item: Any) -> bool:
    checker = getattr(item, "exists", None)
    if not callable(checker):
        return item is not None
    try:
        return bool(checker(timeout=0.1))
    except TypeError:
        try:
            return bool(checker())
        except Exception:
            return False
    except Exception:
        return False


def _safe_is_enabled(item: Any) -> bool:
    checker = getattr(item, "is_enabled", None)
    if not callable(checker):
        return item is not None
    try:
        return bool(checker())
    except Exception:
        return False


def _safe_is_minimized(item: Any) -> bool:
    checker = getattr(item, "is_minimized", None)
    if not callable(checker):
        return False
    try:
        return bool(checker())
    except Exception:
        return False


def _safe_window_text(item: Any) -> str:
    getter = getattr(item, "window_text", None)
    if not callable(getter):
        return ""
    try:
        return str(getter()).strip()
    except Exception:
        return ""


def _normalize_text(value: object) -> str:
    return "\n".join(line.strip() for line in str(value or "").strip().splitlines() if line.strip())


def _build_focus_recommendation(
    *,
    window_ready: bool,
    window_minimized: bool,
    current_chat_ready: bool,
    chat_list_ready: bool,
    input_ready: bool,
) -> str:
    actions: list[str] = []
    if not window_ready:
        actions.append("open_wechat")
    if window_minimized:
        actions.append("restore_window")
    if not current_chat_ready:
        actions.append("select_chat")
    if not chat_list_ready:
        actions.append("wait_chat_messages")
    if not input_ready:
        actions.append("focus_input")
    return ",".join(actions)
