from __future__ import annotations

import inspect
import os
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any, Callable

import pyautogui

from pyweixin import AutoReply, Contacts, GlobalConfig, Messages, Navigator, Tools
from pyweixin.Uielements import Edits as _Edits
from pyweixin.Uielements import Lists as _Lists
from pyweixin.Uielements import Texts as _Texts
from pyweixin.WinSettings import SystemSettings

from .config import MiniMaxSettings, ProfileSettings, ReplySettings
from .app.conversation_store import ConversationStore
from .identity import IdentityRawSignal, IdentityResolver
from .logging_utils import JsonlEventLogger
from .memory.memory_store import MemoryStore
from .message_queue import IncomingMessageEvent, MessageEventQueue
from .minimax_provider import MiniMaxProvider
from .models import Message
from .orchestration.reply_pipeline import ReplyPipeline, ScenePrompts
from . import paths
from .paths import KNOWLEDGE_DIR, LOGS_DIR, MEMORY_DIR, bootstrap_data_dirs
from .profile.profile_store import ProfileStore
from .rag.embeddings import FakeEmbeddings
from .rag.retriever import LocalIndexRetriever
from .reply_scheduler import PendingReplyBatch, ReplyScheduler


Edits = _Edits() if callable(_Edits) else _Edits
Lists = _Lists() if callable(_Lists) else _Lists
Texts = _Texts() if callable(_Texts) else _Texts


@dataclass(slots=True)
class UnreadMessageRecord:
    text: str
    sender_name: str = ""
    signature_key: str = ""


_FORCE_STOP_VK_CODES = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "esc": 0x1B,
    "escape": 0x1B,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


@dataclass(slots=True)
class ForceStopHotkeyMonitor:
    hotkey: str
    key_codes: tuple[int, ...]
    _armed: bool = False

    def poll(self) -> bool:
        if not self.key_codes or not sys.platform.startswith("win"):
            return False
        try:
            import ctypes

            user32 = ctypes.windll.user32
        except Exception:
            return False
        pressed = all(bool(user32.GetAsyncKeyState(code) & 0x8000) for code in self.key_codes)
        if pressed and not self._armed:
            self._armed = True
            return True
        if not pressed:
            self._armed = False
        return False


def _build_force_stop_hotkey_monitor(hotkey: str | None) -> ForceStopHotkeyMonitor | None:
    normalized = str(hotkey or "").strip().lower()
    if not normalized or normalized in {"off", "none", "disabled"}:
        return None
    parts = tuple(part.strip() for part in normalized.split("+") if part.strip())
    if not parts:
        return None
    try:
        key_codes = tuple(_FORCE_STOP_VK_CODES[part] for part in parts)
    except KeyError:
        return None
    return ForceStopHotkeyMonitor(hotkey=normalized, key_codes=key_codes)


class EmergencyStopWatcher:
    def __init__(
        self,
        *,
        hotkey_monitor: object | None = None,
        stop_file: str | os.PathLike[str] | None = None,
        on_trigger: Callable[[str], None] | None = None,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        self.hotkey_monitor = hotkey_monitor
        self.stop_file = Path(stop_file) if stop_file else None
        self.on_trigger = on_trigger or (lambda reason: os._exit(130))
        self.poll_interval_seconds = max(float(poll_interval_seconds), 0.01)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "EmergencyStopWatcher":
        if self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._run, name="wechat-ai-emergency-stop", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_interval_seconds):
            reason = self._poll_reason()
            if reason:
                self.on_trigger(reason)
                return

    def _poll_reason(self) -> str:
        poll = getattr(self.hotkey_monitor, "poll", None)
        if callable(poll):
            try:
                if bool(poll()):
                    return "hotkey"
            except Exception:
                pass
        if self.stop_file is not None:
            try:
                if _stop_file_requested(self.stop_file):
                    return "stop_file"
            except Exception:
                pass
        return ""


def _stop_file_requested(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.read_text(encoding="utf-8", errors="ignore").strip())
    except OSError:
        return True


def _build_profile_store(profile_settings: ProfileSettings) -> ProfileStore:
    store = ProfileStore(base_dir=profile_settings.user_profile_dir.parent)
    store.user_profiles_dir = profile_settings.user_profile_dir
    store.agent_profiles_dir = profile_settings.agent_profile_dir
    return store


def _build_retriever():
    index_path = KNOWLEDGE_DIR / "local_knowledge_index.json"
    if not index_path.exists():
        return None
    return LocalIndexRetriever(index_path=index_path, embeddings=FakeEmbeddings())


def _build_memory_store():
    return MemoryStore(base_dir=MEMORY_DIR)


def _build_event_logger():
    return JsonlEventLogger(path=LOGS_DIR / "runtime_events.jsonl")


def _build_conversation_store():
    return ConversationStore(path=paths.DATA_DIR / "app" / "conversations.json")


def _build_identity_resolver():
    return IdentityResolver(repository=None, event_logger=_build_event_logger())


def _safe_item_text(item: object) -> str:
    getter = getattr(item, "window_text", None)
    if not callable(getter):
        return ""
    try:
        return str(getter()).strip()
    except Exception:
        return ""


def _normalize_dedupe_part(value: object) -> str:
    return " ".join(str(value or "").replace("\u2005", " ").replace("\xa0", " ").split())


def _build_reply_pipeline(provider, minimax: MiniMaxSettings, reply: ReplySettings, profile: ProfileSettings):
    pipeline_kwargs = {
        "provider": provider,
        "prompts": ScenePrompts(
            friend_system_prompt=reply.friend_system_prompt,
            group_system_prompt=reply.group_system_prompt,
        ),
        "context_limit": reply.context_limit,
        "model": minimax.model,
        "profile_store": _build_profile_store(profile),
        "active_agent_id": profile.default_active_agent_id,
        "retriever": _build_retriever(),
        "memory_store": _build_memory_store(),
        "event_logger": _build_event_logger(),
        "prompt_preview_max_chars": getattr(reply, "prompt_preview_max_chars", 400),
    }
    signature = inspect.signature(ReplyPipeline)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return ReplyPipeline(**pipeline_kwargs)
    filtered_kwargs = {
        key: value
        for key, value in pipeline_kwargs.items()
        if key in signature.parameters
    }
    return ReplyPipeline(**filtered_kwargs)


@dataclass(slots=True)
class WeChatAIApp:
    engine: ReplyPipeline
    fallback_reply: str
    mention_names: tuple[str, ...]
    processed_signatures: dict[str, float] = field(default_factory=dict)
    processed_signature_ttl_seconds: float = 1800.0
    processed_signature_limit: int = 1000
    debug: bool = False
    active_merge_window: float = 3.0
    active_pending_session: str | None = None
    active_pending_is_group: bool = False
    active_pending_sender_name: str | None = None
    active_pending_messages: list[str] = field(default_factory=list)
    active_pending_contexts: list[str] = field(default_factory=list)
    active_pending_deadline: float | None = None
    active_last_seen_signature_by_session: dict[str, str] = field(default_factory=dict)
    message_queue: MessageEventQueue = field(default_factory=MessageEventQueue)
    reply_scheduler: ReplyScheduler = field(
        default_factory=lambda: ReplyScheduler(merge_window_seconds=3.0)
    )
    identity_resolver: IdentityResolver = field(default_factory=_build_identity_resolver)
    conversation_store: ConversationStore = field(default_factory=_build_conversation_store)
    send_confirmer: Any | None = None
    stop_event: Any | None = None

    @classmethod
    def from_env(cls) -> "WeChatAIApp":
        bootstrap_data_dirs()
        minimax = MiniMaxSettings.from_env()
        reply = ReplySettings.from_env()
        profile = ProfileSettings.from_env()
        provider = MiniMaxProvider(
            api_key=minimax.api_key,
            api_url=minimax.api_url,
            timeout=minimax.timeout,
        )
        engine = _build_reply_pipeline(provider=provider, minimax=minimax, reply=reply, profile=profile)
        mention_names = reply.group_mention_names
        if not mention_names:
            try:
                my_profile = Contacts.check_my_info(close_weixin=False)
                nickname = ""
                for key in ("昵称", "名稱", "名称", "微信昵称", "显示名"):
                    value = my_profile.get(key)
                    if value:
                        nickname = str(value).strip()
                        break
                mention_names = (nickname,) if nickname else ()
            except Exception:
                mention_names = ()
        try:
            from .app.wechat_window_probe import PyWeixinVisualSendConfirmer

            send_confirmer = PyWeixinVisualSendConfirmer()
        except Exception:
            send_confirmer = None
        return cls(
            engine=engine,
            fallback_reply=reply.fallback_reply,
            mention_names=mention_names,
            send_confirmer=send_confirmer,
        )

    def _debug(self, message: str) -> None:
        if self.debug:
            print(f"[wechat_ai] {message}")

    def _log_event(self, event_type: str, **fields: object) -> None:
        logger = getattr(self.engine, "event_logger", None)
        if logger is None:
            return
        logger.log_event(event_type, **fields)

    def _stop_requested(self) -> bool:
        is_set = getattr(self.stop_event, "is_set", None)
        return bool(callable(is_set) and is_set())

    def _dismiss_wechat_context_menu(self) -> None:
        try:
            pyautogui.press("esc", _pause=False)
        except TypeError:
            try:
                pyautogui.press("esc")
            except Exception:
                pass
        except Exception:
            pass

    def _is_my_bubble_safe(self, main_window: Any, item: Any) -> bool:
        if hasattr(item, "mine"):
            return bool(getattr(item, "mine"))
        checker = getattr(Tools, "is_my_bubble", None)
        if not callable(checker):
            return False
        try:
            return bool(checker(main_window, item))
        finally:
            # pyweixin 4.1 detects bubble ownership by right-clicking the
            # message. Always close the context menu before the next UI action.
            self._dismiss_wechat_context_menu()

    def _parse_message_content_compat(self, item: Any, *, friendtype: str) -> tuple[str, str, str]:
        parser = getattr(Tools, "parse_message_content", None)
        if callable(parser):
            return parser(ListItem=item, friendtype=friendtype)
        text = _safe_item_text(item)
        sender = self._extract_sender_from_item_buttons(item)
        return sender, text, "text"

    def _extract_sender_from_item_buttons(self, item: Any) -> str:
        children = getattr(item, "children", None)
        if not callable(children):
            return ""
        try:
            containers = list(children())
        except Exception:
            return ""
        for container in containers:
            nested_children = getattr(container, "children", None)
            if not callable(nested_children):
                continue
            try:
                buttons = list(nested_children(control_type="Button"))
            except TypeError:
                try:
                    buttons = list(nested_children())
                except Exception:
                    buttons = []
            except Exception:
                buttons = []
            for button in buttons:
                sender = _safe_item_text(button)
                if sender:
                    return sender
        return ""

    def _log_send_skipped_by_stop_event(self, session_name: str, is_group: bool, stage: str) -> None:
        self._debug(f"send skipped by stop_event session={session_name!r} stage={stage}")
        self._log_event(
            "send_skipped_stop_event",
            chat_id=session_name,
            chat_type="group" if is_group else "friend",
            stage=stage,
        )

    def _generate_reply_message(self, message: Message) -> str:
        if hasattr(self.engine, "generate_reply"):
            return self.engine.generate_reply(message)
        if message.chat_type == "group":
            return self.engine.generate_group_reply(message.text, message.context)
        return self.engine.generate_friend_reply(message.text, message.context)

    def _normalize_group_sender_name(self, chat_id: str, sender_name: str | None) -> str:
        normalized_chat_id = str(chat_id or "").strip()
        normalized_sender = str(sender_name or "").strip()
        return normalized_sender or normalized_chat_id

    def friend_callback(
        self,
        new_message: str,
        contexts: list[str],
        *,
        chat_id: str = "friend",
        sender_name: str | None = None,
    ) -> str:
        try:
            reply = self._generate_reply_message(
                Message(
                    chat_id=chat_id,
                    chat_type="friend",
                    sender_name=sender_name or chat_id,
                    text=new_message,
                    context=contexts,
                )
            )
            return reply or self.fallback_reply
        except Exception as exc:
            self._debug(f"friend_callback failed error={type(exc).__name__}: {exc}")
            self._log_event(
                "fallback_used",
                chat_id=chat_id,
                chat_type="friend",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return self.fallback_reply

    def group_callback(
        self,
        new_message: str,
        contexts: list[str],
        *,
        chat_id: str = "group",
        sender_name: str = "",
    ) -> str:
        try:
            reply = self._generate_reply_message(
                Message(
                    chat_id=chat_id,
                    chat_type="group",
                    sender_name=self._normalize_group_sender_name(chat_id, sender_name),
                    text=new_message,
                    context=contexts,
                )
            )
            return reply or self.fallback_reply
        except Exception as exc:
            self._debug(f"group_callback failed error={type(exc).__name__}: {exc}")
            self._log_event(
                "fallback_used",
                chat_id=chat_id,
                chat_type="group",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return self.fallback_reply

    def run_friend_auto_reply(self, friend: str, duration: str, window_minimize: bool = False) -> dict:
        dialog_window = Navigator.open_seperate_dialog_window(
            friend=friend,
            window_minimize=window_minimize,
            close_weixin=False,
        )
        return AutoReply.auto_reply_to_friend(
            dialog_window=dialog_window,
            duration=duration,
            callback=lambda new_message, contexts: self.friend_callback(
                new_message,
                contexts,
                chat_id=friend,
                sender_name=friend,
            ),
            close_dialog_window=True,
        )

    def run_group_at_auto_reply(self, group_name: str, duration: str) -> dict:
        GlobalConfig.close_weixin = False
        main_window = Navigator.open_dialog_window(
            friend=group_name,
            is_maximize=False,
            search_pages=GlobalConfig.search_pages,
        )
        if not Tools.is_group_chat(main_window):
            raise ValueError(f"{group_name} is not a group chat")
        chat_list = main_window.child_window(**Lists.FriendChatList)
        input_edit = main_window.child_window(**Edits.InputEdit)
        Tools.activate_chatList(chat_list)
        initial_runtime_id = 0
        if chat_list.children(control_type="ListItem"):
            initial_runtime_id = chat_list.children(control_type="ListItem")[-1].element_info.runtime_id
        duration_seconds = Tools.match_duration(duration)
        if duration_seconds is None:
            raise ValueError(f"Invalid duration: {duration}")
        end_timestamp = time.time() + duration_seconds
        replies = 0
        SystemSettings.open_listening_mode(volume=False)
        try:
            while time.time() < end_timestamp:
                if not chat_list.children(control_type="ListItem"):
                    continue
                new_message = chat_list.children(control_type="ListItem")[-1]
                runtime_id = new_message.element_info.runtime_id
                if runtime_id == initial_runtime_id:
                    continue
                initial_runtime_id = runtime_id
                if new_message.class_name() != "mmui::ChatTextItemView":
                    continue
                if self._is_my_bubble_safe(main_window, new_message):
                    continue
                message_sender, message_content, _message_type = self._parse_message_content_compat(
                    new_message,
                    friendtype="群聊",
                )
                text = str(message_content).strip()
                if not self._is_group_mention(text):
                    continue
                contexts = [
                    item.window_text()
                    for item in chat_list.children(control_type="ListItem")
                    if item.window_text().strip()
                ]
                reply = self.group_callback(
                    text,
                    contexts,
                    chat_id=group_name,
                    sender_name=self._normalize_group_sender_name(group_name, message_sender),
                )
                input_edit.click_input()
                SystemSettings.copy_text_to_clipboard(reply)
                pyautogui.hotkey("ctrl", "v", _pause=False)
                pyautogui.hotkey("alt", "s", _pause=False)
                replies += 1
        finally:
            SystemSettings.close_listening_mode()
            main_window.close()
        return {"group": group_name, "replies_sent": replies}

    def _build_merged_message(self, messages: list[str]) -> str:
        return "\n".join(message.strip() for message in messages if message.strip())

    def _order_unread_messages(self, unread_messages: list[str], contexts: list[str]) -> list[str]:
        cleaned_messages = [message.strip() for message in unread_messages if isinstance(message, str) and message.strip()]
        if len(cleaned_messages) <= 1:
            return cleaned_messages

        context_timeline = [message.strip() for message in contexts if isinstance(message, str) and message.strip()]
        if len(context_timeline) < len(cleaned_messages):
            return cleaned_messages

        remaining = Counter(cleaned_messages)
        ordered_messages: list[str] = []
        for context_message in context_timeline:
            if remaining.get(context_message, 0) <= 0:
                continue
            ordered_messages.append(context_message)
            remaining[context_message] -= 1

        if len(ordered_messages) != len(cleaned_messages):
            return cleaned_messages
        return ordered_messages

    def _normalize_unread_message_record(self, raw_message: object) -> UnreadMessageRecord | None:
        if isinstance(raw_message, str):
            text = raw_message.strip()
            return UnreadMessageRecord(text=text, signature_key=text) if text else None

        if isinstance(raw_message, dict):
            text_value = (
                raw_message.get("text")
                or raw_message.get("message")
                or raw_message.get("content")
                or raw_message.get("message_content")
            )
            text = str(text_value or "").strip()
            if not text:
                return None
            sender_value = (
                raw_message.get("sender_name")
                or raw_message.get("sender")
                or raw_message.get("nickname")
                or raw_message.get("from")
            )
            sender_name = str(sender_value or "").strip()
            runtime_value = raw_message.get("runtime_id") or raw_message.get("message_id") or raw_message.get("signature")
            signature_key = str(runtime_value or text).strip() or text
            return UnreadMessageRecord(text=text, sender_name=sender_name, signature_key=signature_key)

        if isinstance(raw_message, (tuple, list)) and len(raw_message) >= 2:
            sender_name = str(raw_message[0] or "").strip()
            text = str(raw_message[1] or "").strip()
            if not text:
                return None
            signature_key = str(raw_message[2] if len(raw_message) >= 3 else text).strip() or text
            return UnreadMessageRecord(text=text, sender_name=sender_name, signature_key=signature_key)

        return None

    def _order_unread_message_records(
        self,
        records: list[UnreadMessageRecord],
        contexts: list[str],
    ) -> list[UnreadMessageRecord]:
        if len(records) <= 1:
            return records

        ordered_texts = self._order_unread_messages([record.text for record in records], contexts)
        if ordered_texts == [record.text for record in records]:
            return records

        remaining_by_text: dict[str, list[UnreadMessageRecord]] = {}
        for record in records:
            remaining_by_text.setdefault(record.text, []).append(record)

        ordered_records: list[UnreadMessageRecord] = []
        for text in ordered_texts:
            candidates = remaining_by_text.get(text) or []
            if not candidates:
                return records
            ordered_records.append(candidates.pop(0))
        return ordered_records if len(ordered_records) == len(records) else records

    def _enrich_group_unread_senders_from_visible_items(
        self,
        main_window,
        records: list[UnreadMessageRecord],
    ) -> None:
        unresolved_records = [record for record in records if not record.sender_name.strip()]
        if not unresolved_records or not hasattr(main_window, "child_window"):
            return
        try:
            chat_list = main_window.child_window(**Lists.FriendChatList)
            items = chat_list.children(control_type="ListItem")
        except Exception as exc:
            self._debug(f"enrich group unread sender failed error={type(exc).__name__}: {exc}")
            return

        unresolved_by_text: dict[str, list[UnreadMessageRecord]] = {}
        for record in unresolved_records:
            unresolved_by_text.setdefault(record.text, []).append(record)

        for item in reversed(items):
            try:
                if item.class_name() != "mmui::ChatTextItemView":
                    continue
                if self._is_my_bubble_safe(main_window, item):
                    continue
                message_sender, message_content, _message_type = self._parse_message_content_compat(
                    item,
                    friendtype="群聊",
                )
            except Exception as exc:
                self._debug(f"parse group unread visible item failed error={type(exc).__name__}: {exc}")
                continue
            text = str(message_content or "").strip()
            sender_name = str(message_sender or "").strip()
            if not text or not sender_name:
                continue
            candidates = unresolved_by_text.get(text) or []
            if not candidates:
                continue
            candidates.pop().sender_name = sender_name

    def _log_group_unread_sender(
        self,
        *,
        session_name: str,
        sender_name: str,
        raw_sender_name: str,
        message_text: str,
    ) -> None:
        if raw_sender_name.strip():
            self._log_event(
                "group_sender_detected",
                chat_id=session_name,
                chat_type="group",
                sender_name=sender_name,
                raw_sender_name=raw_sender_name,
                source="unread",
                message_preview=message_text,
            )
            return
        self._log_event(
            "group_sender_unresolved",
            chat_id=session_name,
            chat_type="group",
            fallback_sender_name=sender_name,
            source="unread",
            message_preview=message_text,
        )

    def _cleanup_processed_signatures(self, now: float) -> None:
        if isinstance(self.processed_signatures, set):
            self.processed_signatures = {signature: now for signature in self.processed_signatures}
        if self.processed_signature_ttl_seconds > 0:
            cutoff = now - self.processed_signature_ttl_seconds
            self.processed_signatures = {
                signature: timestamp
                for signature, timestamp in self.processed_signatures.items()
                if timestamp >= cutoff
            }
        if self.processed_signature_limit > 0 and len(self.processed_signatures) > self.processed_signature_limit:
            ordered = sorted(self.processed_signatures.items(), key=lambda item: item[1])
            self.processed_signatures = dict(ordered[-self.processed_signature_limit :])

    def _has_processed_signature(self, signature: str, now: float) -> bool:
        self._cleanup_processed_signatures(now)
        return signature in self.processed_signatures

    def _remember_processed_signature(self, signature: str, now: float) -> None:
        self._cleanup_processed_signatures(now)
        self.processed_signatures[signature] = now
        self._cleanup_processed_signatures(now)

    def _message_dedupe_signature(
        self,
        *,
        session_name: str,
        text: str,
        is_group: bool,
        sender_name: str | None = None,
    ) -> str:
        chat_prefix = "group" if is_group else "friend"
        normalized_session = _normalize_dedupe_part(session_name)
        normalized_text = _normalize_dedupe_part(text)
        normalized_sender = _normalize_dedupe_part(sender_name if is_group else session_name)
        if is_group:
            normalized_sender = normalized_sender or normalized_session
        return f"{chat_prefix}:{normalized_session}\0{normalized_sender}\0{normalized_text}"

    def _legacy_unread_text_signature(self, session_name: str, text: str) -> str:
        return f"{session_name}\0unread\0{text}"

    def _snapshot_latest_visible_signature(self, main_window, session_name: str) -> None:
        if not hasattr(main_window, "child_window"):
            return
        try:
            chat_list = main_window.child_window(**Lists.FriendChatList)
            items = chat_list.children(control_type="ListItem")
        except Exception as exc:
            self._debug(f"snapshot_latest_visible_signature failed session={session_name!r} error={type(exc).__name__}: {exc}")
            return
        if not items:
            return
        self.active_last_seen_signature_by_session[session_name] = self._item_signature(items[-1])

    def _build_identity_signal(
        self,
        *,
        session_name: str,
        message_text: str,
        contexts: list[str],
        is_group: bool,
        sender_name: str | None = None,
    ) -> IdentityRawSignal:
        participant_name = sender_name or session_name
        return IdentityRawSignal(
            conversation_id=f"{'group' if is_group else 'friend'}:{session_name}",
            chat_type="group" if is_group else "friend",
            display_name=participant_name,
            sender_name=participant_name,
            group_name=session_name if is_group else None,
            text=message_text,
            contexts=list(contexts),
        )

    def _build_conversation_id(self, session_name: str, is_group: bool) -> str:
        return f"{'group' if is_group else 'friend'}:{session_name}"

    def _log_message_received(
        self,
        *,
        session_name: str,
        text: str,
        is_group: bool,
        sender_name: str | None = None,
        source: str,
    ) -> None:
        self._log_event(
            "message_received",
            conversation_id=self._build_conversation_id(session_name, is_group),
            chat_id=session_name,
            chat_type="group" if is_group else "friend",
            sender=sender_name or session_name,
            text=text,
            is_group=is_group,
            source=source,
        )
        self._record_conversation_message(
            conversation_id=self._build_conversation_id(session_name, is_group),
            sender=sender_name or session_name,
            text=text,
            direction="incoming",
            title=session_name,
            is_group=is_group,
        )

    def _record_conversation_message(
        self,
        *,
        conversation_id: str,
        sender: str,
        text: str,
        direction: str,
        title: str,
        is_group: bool,
        delivery_status: str = "sent",
    ) -> None:
        try:
            self.conversation_store.append_message(
                conversation_id,
                sender=sender,
                text=text,
                direction=direction,
                title=title,
                is_group=is_group,
                delivery_status=delivery_status,
            )
        except Exception as exc:
            self._debug(f"record_conversation_message failed conversation_id={conversation_id!r} error={type(exc).__name__}: {exc}")

    def _send_reply(
        self,
        session_name: str,
        message_text: str,
        contexts: list[str],
        is_group: bool,
        *,
        sender_name: str | None = None,
        ignore_stop_event: bool = False,
    ) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        if not message_text.strip():
            return result
        if not ignore_stop_event and self._stop_requested():
            self._log_send_skipped_by_stop_event(session_name, is_group, "before_generation")
            return result
        identity_result = self.identity_resolver.resolve(
            self._build_identity_signal(
                session_name=session_name,
                message_text=message_text,
                contexts=contexts,
                is_group=is_group,
                sender_name=sender_name,
            )
        )
        try:
            reply = self._generate_reply_message(
                Message(
                    chat_id=session_name,
                    chat_type="group" if is_group else "friend",
                    sender_name=sender_name or session_name,
                    text=message_text,
                    context=contexts,
                    resolved_user_id=identity_result.resolved_user_id,
                    conversation_id=identity_result.conversation_id,
                    participant_display_name=identity_result.participant_display_name,
                    relationship_to_me=identity_result.relationship_to_me,
                    current_intent=identity_result.current_intent,
                    identity_confidence=identity_result.identity_confidence,
                    identity_status=identity_result.identity_status,
                    identity_evidence=list(identity_result.evidence),
                )
            )
            reply = reply or self.fallback_reply
        except Exception as exc:
            self._debug(f"_send_reply failed session={session_name!r} error={type(exc).__name__}: {exc}")
            self._log_event(
                "fallback_used",
                chat_id=session_name,
                chat_type="group" if is_group else "friend",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            reply = self.fallback_reply
        if not ignore_stop_event and self._stop_requested():
            self._log_send_skipped_by_stop_event(session_name, is_group, "before_send")
            return result
        self._debug(f"send_reply session={session_name!r} is_group={is_group} text={message_text!r} reply={reply!r}")
        Messages.send_messages_to_friend(
            friend=session_name,
            messages=[reply],
            close_weixin=False,
        )
        confirmation_required = self.send_confirmer is not None
        if confirmation_required:
            try:
                confirmed = bool(
                    self.send_confirmer.confirm_sent(
                        conversation_id=f"{'group' if is_group else 'friend'}:{session_name}",
                        text=reply,
                        is_group=is_group,
                        send_result={"sent": True},
                    )
                )
            except Exception as exc:
                confirmed = False
                reason = f"{type(exc).__name__}: {exc}"
            else:
                reason = ""
            if not confirmed:
                self._record_conversation_message(
                    conversation_id=self._build_conversation_id(session_name, is_group),
                    sender="assistant",
                    text=reply,
                    direction="outgoing",
                    title=session_name,
                    is_group=is_group,
                    delivery_status="unconfirmed",
                )
                result["errors"] += 1
                self._log_event(
                    "message_send_unconfirmed",
                    chat_id=session_name,
                    chat_type="group" if is_group else "friend",
                    reply_preview=reply,
                    reason=reason,
                )
                return result
        else:
            confirmed = False
        if is_group:
            result["group_replies"] += 1
        else:
            result["friend_replies"] += 1
        self._log_event(
            "message_sent",
            chat_id=session_name,
            chat_type="group" if is_group else "friend",
            reply_preview=reply,
            used_fallback=reply == self.fallback_reply,
            confirmed=confirmed,
            confirmation_required=confirmation_required,
        )
        self._record_conversation_message(
            conversation_id=self._build_conversation_id(session_name, is_group),
            sender="assistant",
            text=reply,
            direction="outgoing",
            title=session_name,
            is_group=is_group,
        )
        return result

    def _flush_active_pending(
        self,
        now: float,
        current_session_name: str | None = None,
        *,
        force: bool = False,
        reason: str | None = None,
    ) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        if not self.active_pending_session or not self.active_pending_messages:
            return result

        should_flush = force
        if current_session_name and current_session_name != self.active_pending_session:
            should_flush = True
        elif self.active_pending_deadline is not None and now >= self.active_pending_deadline:
            should_flush = True
        if not should_flush:
            return result

        pending_session = self.active_pending_session
        pending_messages = list(self.active_pending_messages)
        pending_is_group = self.active_pending_is_group
        pending_sender_name = self.active_pending_sender_name
        try:
            merged_message = self._build_merged_message(self.active_pending_messages)
            if merged_message:
                send_result = self._send_reply(
                    session_name=self.active_pending_session,
                    message_text=merged_message,
                    contexts=self.active_pending_contexts,
                    is_group=self.active_pending_is_group,
                    sender_name=pending_sender_name,
                    ignore_stop_event=force,
                )
                result["friend_replies"] += send_result["friend_replies"]
                result["group_replies"] += send_result["group_replies"]
                result["errors"] += send_result["errors"]
                if force:
                    self._log_event(
                        "shutdown_flush",
                        chat_id=pending_session,
                        chat_type="group" if pending_is_group else "friend",
                        pending_count=len(pending_messages),
                        reason=reason or "shutdown",
                    )
        except Exception as exc:
            self._debug(f"flush_active_pending failed session={self.active_pending_session!r} error={type(exc).__name__}: {exc}")
            result["errors"] += 1
        finally:
            self.active_pending_session = None
            self.active_pending_is_group = False
            self.active_pending_sender_name = None
            self.active_pending_messages = []
            self.active_pending_contexts = []
            self.active_pending_deadline = None
        return result

    def _send_reply_batch(
        self,
        batch: PendingReplyBatch,
        *,
        force: bool = False,
        reason: str | None = None,
    ) -> dict[str, int]:
        is_group = batch.chat_type == "group"
        send_result = self._send_reply(
            session_name=batch.session_name,
            message_text=self._build_merged_message(batch.messages),
            contexts=batch.contexts,
            is_group=is_group,
            sender_name=batch.sender_name,
            ignore_stop_event=force,
        )
        if force:
            self._log_event(
                "shutdown_flush",
                chat_id=batch.session_name,
                chat_type=batch.chat_type,
                pending_count=len(batch.messages),
                reason=reason or "shutdown",
            )
        return send_result

    def _drain_reply_scheduler(self, now: float) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        for batch in self.reply_scheduler.drain_ready(now):
            send_result = self._send_reply_batch(batch)
            result["friend_replies"] += send_result["friend_replies"]
            result["group_replies"] += send_result["group_replies"]
            result["errors"] += send_result["errors"]
        return result

    def _flush_reply_scheduler(
        self,
        *,
        reason: str = "shutdown",
    ) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        for batch in self.reply_scheduler.flush_all(reason=reason):
            send_result = self._send_reply_batch(batch, force=True, reason=reason)
            result["friend_replies"] += send_result["friend_replies"]
            result["group_replies"] += send_result["group_replies"]
            result["errors"] += send_result["errors"]
        return result

    def process_unread_session(self, session_name: str, unread_messages: list[object]) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        if not unread_messages:
            return result

        self._debug(f"process_unread_session session={session_name!r} unread_messages={unread_messages!r}")
        main_window = Navigator.open_dialog_window(
            friend=session_name,
            is_maximize=False,
            search_pages=GlobalConfig.search_pages,
        )
        try:
            is_group = Tools.is_group_chat(main_window)
            unread_records = [
                record
                for record in (self._normalize_unread_message_record(raw_message) for raw_message in unread_messages)
                if record is not None
            ]
            if not unread_records:
                return result
            if is_group:
                self._enrich_group_unread_senders_from_visible_items(main_window, unread_records)
            contexts = list(
                Messages.pull_messages(
                    friend=session_name,
                    number=max(len(unread_records), getattr(self.engine, "context_limit", len(unread_records)) or len(unread_records)),
                    close_weixin=False,
                    search_pages=GlobalConfig.search_pages,
                )
            )
            if not contexts:
                contexts = [record.text for record in unread_records]
            ordered_unread_records = self._order_unread_message_records(unread_records, contexts)
            pending_messages: list[str] = []
            pending_signatures: list[str] = []
            pending_sender_name: str | None = None
            now = time.time()
            for unread_record in ordered_unread_records:
                text = unread_record.text.strip()
                if not text:
                    continue
                if is_group and not self._is_group_mention(text):
                    self._debug(f"skip group unread without mention session={session_name!r} text={text!r}")
                    self._remember_processed_signature(self._legacy_unread_text_signature(session_name, text), now)
                    continue
                sender_name = (
                    self._normalize_group_sender_name(session_name, unread_record.sender_name)
                    if is_group
                    else session_name
                )
                signature = self._message_dedupe_signature(
                    session_name=session_name,
                    text=text,
                    is_group=is_group,
                    sender_name=sender_name,
                )
                legacy_signature = self._legacy_unread_text_signature(session_name, text)
                if self._has_processed_signature(signature, now):
                    continue
                if not is_group and self._has_processed_signature(legacy_signature, now):
                    continue
                self._log_message_received(
                    session_name=session_name,
                    text=text,
                    is_group=is_group,
                    sender_name=sender_name,
                    source="unread",
                )
                pending_messages.append(text)
                pending_signatures.append(signature)
                if is_group:
                    pending_sender_name = sender_name
                    self._log_group_unread_sender(
                        session_name=session_name,
                        sender_name=sender_name,
                        raw_sender_name=unread_record.sender_name,
                        message_text=text,
                    )

            if not pending_messages:
                return result

            self._snapshot_latest_visible_signature(main_window, session_name)
            send_result = self._send_reply(
                session_name=session_name,
                message_text=self._build_merged_message(pending_messages),
                contexts=contexts,
                is_group=is_group,
                sender_name=pending_sender_name,
            )
            result["friend_replies"] += send_result["friend_replies"]
            result["group_replies"] += send_result["group_replies"]
            result["errors"] += send_result["errors"]
            for signature in pending_signatures:
                self._remember_processed_signature(signature, now)
            return result
        except Exception as exc:
            self._debug(f"process_unread_session failed session={session_name!r} error={type(exc).__name__}: {exc}")
            result["errors"] += 1
            return result
        finally:
            if hasattr(main_window, "close"):
                try:
                    main_window.close()
                except Exception:
                    pass

    def _item_signature(self, item) -> str:
        runtime_id = getattr(item.element_info, "runtime_id", None)
        class_name = ""
        text = ""
        try:
            class_name = item.class_name()
        except Exception:
            pass
        text = _safe_item_text(item)
        return f"{runtime_id}|{class_name}|{text}"

    def _parse_incoming_item(self, main_window, item, is_group: bool) -> tuple[str, str]:
        if not is_group:
            return item.window_text().strip(), ""
        try:
            message_sender, message_content, _message_type = self._parse_message_content_compat(
                item,
                friendtype="群聊",
            )
            return str(message_content).strip(), self._normalize_group_sender_name("", str(message_sender))
        except Exception as exc:
            self._debug(f"parse active group item failed error={type(exc).__name__}: {exc}")
            return item.window_text().strip(), ""

    def _collect_active_incoming_messages(
        self,
        main_window,
        session_name: str,
        captured_at: float,
    ) -> tuple[bool, list[IncomingMessageEvent], list[str], str | None]:
        chat_list = main_window.child_window(**Lists.FriendChatList)
        if hasattr(Tools, "activate_chatList"):
            try:
                Tools.activate_chatList(chat_list)
            except Exception as exc:
                self._debug(f"activate_chatList failed session={session_name!r} error={type(exc).__name__}: {exc}")
        items = chat_list.children(control_type="ListItem")
        if not items:
            return False, [], [], None

        is_group = Tools.is_group_chat(main_window)
        chat_type = "group" if is_group else "friend"
        contexts = [item.window_text() for item in items if item.window_text().strip()]
        latest_signature = self._item_signature(items[-1])
        previous_signature = self.active_last_seen_signature_by_session.get(session_name)
        if previous_signature is None:
            self.active_last_seen_signature_by_session[session_name] = latest_signature
            self._debug(f"bootstrap active session={session_name!r} visible_items={len(items)} latest_signature={latest_signature!r}")
            return is_group, [], contexts, None
        candidate_items: list[object] = []
        found_previous = False
        for item in reversed(items):
            signature = self._item_signature(item)
            if signature == previous_signature:
                found_previous = True
                break
            candidate_items.append(item)
        self.active_last_seen_signature_by_session[session_name] = latest_signature
        if not found_previous:
            self._debug(f"active anchor missed session={session_name!r} previous_signature={previous_signature!r}")
            self._log_event(
                "active_anchor_missed",
                **self._build_active_anchor_missed_event(
                    session_name=session_name,
                    previous_signature=previous_signature,
                    latest_signature=latest_signature,
                    items=items,
                    candidate_items=candidate_items,
                ),
            )
            return is_group, [], contexts, None

        events: list[IncomingMessageEvent] = []
        sender_name: str | None = None
        for item in reversed(candidate_items):
            text, parsed_sender_name = self._parse_incoming_item(main_window, item, is_group)
            if not text:
                continue
            if item.class_name() != "mmui::ChatTextItemView":
                continue
            if self._is_my_bubble_safe(main_window, item):
                continue
            event_sender_name = parsed_sender_name if is_group else session_name
            cross_source_signature = self._message_dedupe_signature(
                session_name=session_name,
                text=text,
                is_group=is_group,
                sender_name=event_sender_name,
            )
            legacy_cross_source_signature = self._legacy_unread_text_signature(session_name, text)
            if self._has_processed_signature(cross_source_signature, captured_at) or (
                not is_group and self._has_processed_signature(legacy_cross_source_signature, captured_at)
            ):
                self._debug(f"active skip already processed session={session_name!r} text={text!r}")
                continue
            if is_group and not self._is_group_mention(text):
                self._debug(f"active group skip without mention session={session_name!r} text={text!r}")
                continue
            if is_group and parsed_sender_name and sender_name is None:
                sender_name = parsed_sender_name
            self._log_message_received(
                session_name=session_name,
                text=text,
                is_group=is_group,
                sender_name=event_sender_name,
                source="active",
            )
            events.append(
                IncomingMessageEvent(
                    session_name=session_name,
                    chat_type=chat_type,
                    text=text,
                    contexts=contexts,
                    sender_name=event_sender_name,
                    source="active",
                    signature=f"{session_name}\0active\0{self._item_signature(item)}",
                    captured_at=captured_at,
                )
            )
        return is_group, events, contexts, sender_name

    def _build_active_anchor_missed_event(
        self,
        *,
        session_name: str,
        previous_signature: str,
        latest_signature: str,
        items: list[object],
        candidate_items: list[object],
    ) -> dict[str, object]:
        visible_texts = [_safe_item_text(item) for item in items]
        visible_signatures = [self._item_signature(item) for item in items]
        first_visible_text = next((text for text in visible_texts if text), "")
        latest_visible_text = next((text for text in reversed(visible_texts) if text), "")
        diagnosis = ["anchor_not_visible"]
        if not items:
            diagnosis.append("empty_visible_list")
        elif len(candidate_items) == len(items):
            diagnosis.append("all_visible_items_after_anchor")
        if previous_signature and latest_signature and previous_signature.split("|")[-1] == latest_signature.split("|")[-1]:
            diagnosis.append("same_text_runtime_changed")
        return {
            "chat_id": session_name,
            "previous_signature": previous_signature,
            "latest_signature": latest_signature,
            "visible_items": len(items),
            "candidate_count": len(candidate_items),
            "first_visible_text": first_visible_text,
            "latest_visible_text": latest_visible_text,
            "visible_signature_sample": visible_signatures[-3:],
            "diagnosis": ",".join(diagnosis),
            "recovery_strategy": "reanchor_without_reply",
        }

    def process_active_chat_session(self, now: float | None = None) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        if now is None:
            now = time.time()

        current_session_name: str | None = None
        try:
            drain_result = self._drain_reply_scheduler(now)
            result["friend_replies"] += drain_result["friend_replies"]
            result["group_replies"] += drain_result["group_replies"]
            result["errors"] += drain_result["errors"]

            main_window = Navigator.open_weixin(is_maximize=False)
            current_chat_label = main_window.child_window(**Texts.CurrentChatText)
            if hasattr(current_chat_label, "exists") and not current_chat_label.exists(timeout=0.1):
                flush_result = self._flush_active_pending(now=now)
                result["friend_replies"] += flush_result["friend_replies"]
                result["group_replies"] += flush_result["group_replies"]
                result["errors"] += flush_result["errors"]
                return result

            current_session_name = current_chat_label.window_text().strip()
            if not current_session_name:
                flush_result = self._flush_active_pending(now=now)
                result["friend_replies"] += flush_result["friend_replies"]
                result["group_replies"] += flush_result["group_replies"]
                result["errors"] += flush_result["errors"]
                return result

            self.reply_scheduler.merge_window_seconds = self.active_merge_window
            _is_group, events, _contexts, _sender_name = self._collect_active_incoming_messages(
                main_window,
                current_session_name,
                captured_at=now,
            )
            accepted = self.message_queue.enqueue_many(events)
            if accepted:
                self._debug(f"active session={current_session_name!r} queued_events={accepted}")
            ready_batches = self.message_queue.drain_ready(now)
            for batch in ready_batches:
                scheduled = self.reply_scheduler.add_message(
                    session_name=batch.session_name,
                    chat_type=batch.chat_type,
                    text=batch.text,
                    contexts=batch.contexts,
                    sender_name=batch.sender_name,
                    now=now,
                )
                for ready in scheduled:
                    send_result = self._send_reply_batch(ready)
                    result["friend_replies"] += send_result["friend_replies"]
                    result["group_replies"] += send_result["group_replies"]
                    result["errors"] += send_result["errors"]

            flush_result = self._drain_reply_scheduler(now)
            result["friend_replies"] += flush_result["friend_replies"]
            result["group_replies"] += flush_result["group_replies"]
            result["errors"] += flush_result["errors"]
            return result
        except Exception as exc:
            self._debug(f"process_active_chat_session failed error={type(exc).__name__}: {exc}")
            result["errors"] += 1
            return result

    def run_global_auto_reply(
        self,
        duration: str,
        poll_interval: float = 1.0,
        *,
        forever: bool = False,
        heartbeat_interval: float = 60.0,
        error_backoff_seconds: float = 5.0,
        stop_event: object | None = None,
        stop_hotkey: str | None = None,
        stop_hotkey_monitor: object | None = None,
    ) -> dict[str, int | float]:
        duration_seconds = Tools.match_duration(duration)
        if duration_seconds is None:
            raise ValueError(f"Invalid duration: {duration}")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than 0")
        if error_backoff_seconds <= 0:
            raise ValueError("error_backoff_seconds must be greater than 0")

        stats: dict[str, int | float] = {
            "duration_seconds": duration_seconds,
            "poll_interval": poll_interval,
            "polls": 0,
            "sessions": 0,
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        self._debug(
            f"global auto reply start mention_names={self.mention_names!r} duration={duration!r} poll_interval={poll_interval} active_merge_window={self.active_merge_window} forever={forever} heartbeat_interval={heartbeat_interval} error_backoff_seconds={error_backoff_seconds}"
        )
        previous_stop_event = self.stop_event
        if stop_event is not None:
            self.stop_event = stop_event
        hotkey_monitor = stop_hotkey_monitor if stop_hotkey_monitor is not None else _build_force_stop_hotkey_monitor(stop_hotkey)
        end_timestamp = None if forever else time.time() + duration_seconds
        next_heartbeat_at = time.time() + heartbeat_interval if heartbeat_interval > 0 else None
        consecutive_loop_errors = 0
        stop_event_logged = False
        force_stop_logged = False

        def stop_requested() -> bool:
            return self._stop_requested()

        def hotkey_stop_requested() -> bool:
            nonlocal force_stop_logged
            if hotkey_monitor is None or not hasattr(hotkey_monitor, "poll"):
                return False
            if not bool(getattr(hotkey_monitor, "poll")()):
                return False
            if not force_stop_logged:
                hotkey_name = getattr(hotkey_monitor, "hotkey", stop_hotkey or "unknown")
                self._debug(f"global auto reply force stop hotkey triggered hotkey={hotkey_name!r}")
                self._log_event(
                    "force_stop_hotkey_triggered",
                    hotkey=hotkey_name,
                    polls=stats["polls"],
                    sessions=stats["sessions"],
                    friend_replies=stats["friend_replies"],
                    group_replies=stats["group_replies"],
                    errors=stats["errors"],
                )
                force_stop_logged = True
            return True

        def record_stop_event() -> None:
            nonlocal stop_event_logged
            if stop_event_logged:
                return
            self._debug("global auto reply stop_event received")
            self._log_event(
                "stop_event_received",
                polls=stats["polls"],
                sessions=stats["sessions"],
                friend_replies=stats["friend_replies"],
                group_replies=stats["group_replies"],
                errors=stats["errors"],
            )
            stop_event_logged = True

        def sleep_or_stop(seconds: float) -> bool:
            if hotkey_monitor is None:
                if stop_event is not None and hasattr(stop_event, "wait"):
                    return bool(getattr(stop_event, "wait")(seconds))
                time.sleep(seconds)
                return stop_requested()
            if seconds <= 0:
                return stop_requested() or hotkey_stop_requested()
            deadline = time.time() + seconds
            while True:
                if stop_requested() or hotkey_stop_requested():
                    return True
                remaining = deadline - time.time()
                if remaining <= 0:
                    return stop_requested() or hotkey_stop_requested()
                chunk = min(0.1, remaining)
                if stop_event is not None and hasattr(stop_event, "wait"):
                    if bool(getattr(stop_event, "wait")(chunk)):
                        return True
                    continue
                time.sleep(chunk)

        while True:
            now = time.time()
            if stop_requested() or hotkey_stop_requested():
                record_stop_event()
                break
            if end_timestamp is not None and now >= end_timestamp:
                break
            if next_heartbeat_at is not None and now >= next_heartbeat_at:
                self._debug(
                    f"heartbeat polls={stats['polls']} sessions={stats['sessions']} friend_replies={stats['friend_replies']} group_replies={stats['group_replies']} errors={stats['errors']}"
                )
                self._log_event(
                    "heartbeat",
                    polls=stats["polls"],
                    sessions=stats["sessions"],
                    friend_replies=stats["friend_replies"],
                    group_replies=stats["group_replies"],
                    errors=stats["errors"],
                )
                next_heartbeat_at = now + heartbeat_interval
            try:
                unread_sessions = Messages.check_new_messages(close_weixin=False)
                stats["polls"] += 1
                self._debug(f"poll={stats['polls']} unread_sessions={unread_sessions!r}")
                for session_name, unread_messages in unread_sessions.items():
                    stats["sessions"] += 1
                    session_result = self.process_unread_session(session_name, unread_messages)
                    stats["friend_replies"] += session_result["friend_replies"]
                    stats["group_replies"] += session_result["group_replies"]
                    stats["errors"] += session_result["errors"]
                active_result = self.process_active_chat_session(now=now)
                stats["friend_replies"] += active_result["friend_replies"]
                stats["group_replies"] += active_result["group_replies"]
                stats["errors"] += active_result["errors"]
                consecutive_loop_errors = 0
                if end_timestamp is not None and time.time() >= end_timestamp:
                    break
                if stop_requested() or hotkey_stop_requested():
                    record_stop_event()
                    break
                if sleep_or_stop(poll_interval):
                    record_stop_event()
                    break
            except KeyboardInterrupt:
                self._debug("global auto reply interrupted by keyboard")
                break
            except Exception as exc:
                consecutive_loop_errors += 1
                stats["errors"] += 1
                backoff_seconds = min(error_backoff_seconds * (2 ** (consecutive_loop_errors - 1)), 60.0)
                self._debug(
                    f"global auto reply loop error={type(exc).__name__}: {exc} consecutive={consecutive_loop_errors} backoff={backoff_seconds}"
                )
                self._log_event(
                    "loop_error",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    consecutive_errors=consecutive_loop_errors,
                    backoff_seconds=backoff_seconds,
                )
                if sleep_or_stop(backoff_seconds):
                    record_stop_event()
                    break

        try:
            flush_result = self._flush_reply_scheduler(reason="shutdown")
            stats["friend_replies"] += flush_result["friend_replies"]
            stats["group_replies"] += flush_result["group_replies"]
            stats["errors"] += flush_result["errors"]
            flush_result = self._flush_active_pending(now=time.time(), force=True, reason="shutdown")
            stats["friend_replies"] += flush_result["friend_replies"]
            stats["group_replies"] += flush_result["group_replies"]
            stats["errors"] += flush_result["errors"]
            return stats
        finally:
            self.stop_event = previous_stop_event

    def _is_group_mention(self, text: str) -> bool:
        normalized = text.replace("＠", "@").replace("\u2005", " ").replace("\xa0", " ")
        if "@所有人" in normalized:
            return True
        if "@" not in normalized:
            return False
        return any(name and f"@{name}" in normalized for name in self.mention_names)
