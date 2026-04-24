from __future__ import annotations

import inspect
import time
from collections import Counter
from dataclasses import dataclass
from dataclasses import field

import pyautogui

from pyweixin import AutoReply, Contacts, GlobalConfig, Messages, Navigator, Tools
from pyweixin.Uielements import Edits as _Edits
from pyweixin.Uielements import Lists as _Lists
from pyweixin.Uielements import Texts as _Texts
from pyweixin.WinSettings import SystemSettings

from .config import MiniMaxSettings, ProfileSettings, ReplySettings
from .identity import IdentityRawSignal, IdentityResolver
from .logging_utils import JsonlEventLogger
from .memory.memory_store import MemoryStore
from .message_queue import IncomingMessageEvent, MessageEventQueue
from .minimax_provider import MiniMaxProvider
from .models import Message
from .orchestration.reply_pipeline import ReplyPipeline, ScenePrompts
from .paths import KNOWLEDGE_DIR, LOGS_DIR, MEMORY_DIR, bootstrap_data_dirs
from .profile.profile_store import ProfileStore
from .rag.embeddings import FakeEmbeddings
from .rag.retriever import LocalIndexRetriever
from .reply_scheduler import PendingReplyBatch, ReplyScheduler


Edits = _Edits() if callable(_Edits) else _Edits
Lists = _Lists() if callable(_Lists) else _Lists
Texts = _Texts() if callable(_Texts) else _Texts


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


def _build_identity_resolver():
    return IdentityResolver(repository=None, event_logger=_build_event_logger())


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
        return cls(engine=engine, fallback_reply=reply.fallback_reply, mention_names=mention_names)

    def _debug(self, message: str) -> None:
        if self.debug:
            print(f"[wechat_ai] {message}")

    def _log_event(self, event_type: str, **fields: object) -> None:
        logger = getattr(self.engine, "event_logger", None)
        if logger is None:
            return
        logger.log_event(event_type, **fields)

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
                if Tools.is_my_bubble(main_window, new_message):
                    continue
                message_sender, message_content, _message_type = Tools.parse_message_content(
                    ListItem=new_message,
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

    def _send_reply(
        self,
        session_name: str,
        message_text: str,
        contexts: list[str],
        is_group: bool,
        *,
        sender_name: str | None = None,
    ) -> dict[str, int]:
        result = {"friend_replies": 0, "group_replies": 0, "errors": 0}
        if not message_text.strip():
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
        if is_group:
            result["group_replies"] += 1
        else:
            result["friend_replies"] += 1
        self._debug(f"send_reply session={session_name!r} is_group={is_group} text={message_text!r} reply={reply!r}")
        Messages.send_messages_to_friend(
            friend=session_name,
            messages=[reply],
            close_weixin=False,
        )
        self._log_event(
            "message_sent",
            chat_id=session_name,
            chat_type="group" if is_group else "friend",
            reply_preview=reply,
            used_fallback=reply == self.fallback_reply,
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

    def process_unread_session(self, session_name: str, unread_messages: list[str]) -> dict[str, int]:
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
            contexts = list(
                Messages.pull_messages(
                    friend=session_name,
                    number=max(len(unread_messages), getattr(self.engine, "context_limit", len(unread_messages)) or len(unread_messages)),
                    close_weixin=False,
                    search_pages=GlobalConfig.search_pages,
                )
            )
            if not contexts:
                contexts = list(unread_messages)
            ordered_unread_messages = self._order_unread_messages(unread_messages, contexts)
            pending_messages: list[str] = []
            pending_signatures: list[str] = []
            now = time.time()
            for unread_message in ordered_unread_messages:
                if not isinstance(unread_message, str):
                    continue
                text = unread_message.strip()
                if not text:
                    continue
                signature = f"{session_name}\0unread\0{text}"
                if self._has_processed_signature(signature, now):
                    continue
                if is_group and not self._is_group_mention(text):
                    self._debug(f"skip group unread without mention session={session_name!r} text={text!r}")
                    self._remember_processed_signature(signature, now)
                    continue
                pending_messages.append(text)
                pending_signatures.append(signature)

            if not pending_messages:
                return result

            self._snapshot_latest_visible_signature(main_window, session_name)
            send_result = self._send_reply(
                session_name=session_name,
                message_text=self._build_merged_message(pending_messages),
                contexts=contexts,
                is_group=is_group,
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
        try:
            text = item.window_text().strip()
        except Exception:
            pass
        return f"{runtime_id}|{class_name}|{text}"

    def _parse_incoming_item(self, main_window, item, is_group: bool) -> tuple[str, str]:
        if not is_group:
            return item.window_text().strip(), ""
        try:
            message_sender, message_content, _message_type = Tools.parse_message_content(
                ListItem=item,
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
                chat_id=session_name,
                previous_signature=previous_signature,
                latest_signature=latest_signature,
                visible_items=len(items),
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
            if Tools.is_my_bubble(main_window, item):
                continue
            if is_group and not self._is_group_mention(text):
                self._debug(f"active group skip without mention session={session_name!r} text={text!r}")
                continue
            if is_group and parsed_sender_name and sender_name is None:
                sender_name = parsed_sender_name
            event_sender_name = parsed_sender_name if is_group else session_name
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
        end_timestamp = None if forever else time.time() + duration_seconds
        next_heartbeat_at = time.time() + heartbeat_interval if heartbeat_interval > 0 else None
        consecutive_loop_errors = 0

        while True:
            now = time.time()
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
                time.sleep(poll_interval)
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
                time.sleep(backoff_seconds)

        flush_result = self._flush_reply_scheduler(reason="shutdown")
        stats["friend_replies"] += flush_result["friend_replies"]
        stats["group_replies"] += flush_result["group_replies"]
        stats["errors"] += flush_result["errors"]
        flush_result = self._flush_active_pending(now=time.time(), force=True, reason="shutdown")
        stats["friend_replies"] += flush_result["friend_replies"]
        stats["group_replies"] += flush_result["group_replies"]
        stats["errors"] += flush_result["errors"]
        return stats

    def _is_group_mention(self, text: str) -> bool:
        normalized = text.replace("＠", "@").replace("\u2005", " ").replace("\xa0", " ")
        if "@所有人" in normalized:
            return True
        if "@" not in normalized:
            return False
        return any(name and f"@{name}" in normalized for name in self.mention_names)
