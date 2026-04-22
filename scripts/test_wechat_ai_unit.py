from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.context import build_context_window  # type: ignore  # noqa: E402
from wechat_ai.logging_utils import JsonlEventLogger, tail_jsonl_events  # type: ignore  # noqa: E402
from wechat_ai.memory.memory_store import MemoryStore  # type: ignore  # noqa: E402
from wechat_ai.minimax_provider import MiniMaxProvider  # type: ignore  # noqa: E402
from wechat_ai.reply_engine import ReplyEngine, ScenePrompts  # type: ignore  # noqa: E402


def import_wechat_runtime_with_stubs():
    pyautogui_stub = types.ModuleType("pyautogui")
    pyautogui_stub.hotkey = lambda *args, **kwargs: None

    pyweixin_stub = types.ModuleType("pyweixin")
    pyweixin_stub.AutoReply = object()
    pyweixin_stub.Contacts = object()
    pyweixin_stub.GlobalConfig = types.SimpleNamespace(close_weixin=False, search_pages=5)
    pyweixin_stub.Navigator = object()
    pyweixin_stub.Tools = object()
    pyweixin_stub.Messages = object()

    uielements_stub = types.ModuleType("pyweixin.Uielements")
    uielements_stub.Edits = types.SimpleNamespace(InputEdit={"_kind": "InputEdit"})
    uielements_stub.Lists = types.SimpleNamespace(FriendChatList={"_kind": "FriendChatList"})
    uielements_stub.Texts = types.SimpleNamespace(CurrentChatText={"_kind": "CurrentChatText"})

    winsettings_stub = types.ModuleType("pyweixin.WinSettings")
    winsettings_stub.SystemSettings = types.SimpleNamespace(
        open_listening_mode=lambda **kwargs: None,
        close_listening_mode=lambda: None,
        copy_text_to_clipboard=lambda text: None,
    )

    original_modules = {
        name: sys.modules.get(name)
        for name in ("pyautogui", "pyweixin", "pyweixin.Uielements", "pyweixin.WinSettings", "wechat_ai.wechat_runtime")
    }
    sys.modules["pyautogui"] = pyautogui_stub
    sys.modules["pyweixin"] = pyweixin_stub
    sys.modules["pyweixin.Uielements"] = uielements_stub
    sys.modules["pyweixin.WinSettings"] = winsettings_stub
    sys.modules.pop("wechat_ai.wechat_runtime", None)
    try:
        return importlib.import_module("wechat_ai.wechat_runtime")
    finally:
        for name, module in original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class ReplyEngineTests(unittest.TestCase):
    def test_context_window_keeps_latest_ten_messages(self) -> None:
        contexts = [f"msg-{index}" for index in range(15)]
        window = build_context_window(contexts, limit=10)
        self.assertEqual(window[0], "msg-5")
        self.assertEqual(window[-1], "msg-14")
        self.assertEqual(len(window), 10)

    def test_provider_builds_minimax_payload_and_parses_reply(self) -> None:
        captured: dict[str, object] = {}

        def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object], timeout: int) -> dict[str, object]:
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = payload
            captured["timeout"] = timeout
            return {
                "choices": [
                    {
                        "message": {
                            "content": "test-reply"
                        }
                    }
                ]
            }

        provider = MiniMaxProvider(api_key="demo-key", transport=fake_transport)
        reply = provider.complete(
            system_prompt="you are an assistant",
            user_prompt="hello",
            model="MiniMax-M2.5",
        )

        self.assertEqual(reply, "test-reply")
        self.assertEqual(captured["url"], "https://api.minimaxi.com/v1/text/chatcompletion_v2")
        self.assertEqual(captured["timeout"], 30)
        payload = captured["payload"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "MiniMax-M2.5")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "hello")

    def test_reply_engine_uses_scene_specific_prompts_and_context(self) -> None:
        calls: list[dict[str, str]] = []

        class FakeProvider:
            def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
                calls.append(
                    {
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "model": model or "",
                    }
                )
                return "model-output"

        engine = ReplyEngine(
            provider=FakeProvider(),
            prompts=ScenePrompts(
                friend_system_prompt="friend-prompt",
                group_system_prompt="group-prompt",
            ),
            context_limit=10,
            model="MiniMax-M2.5",
        )

        reply = engine.generate_friend_reply(
            latest_message="are you busy",
            contexts=["hello", "are you there", "are you busy"],
        )
        self.assertEqual(reply, "model-output")
        self.assertEqual(calls[0]["system_prompt"], "friend-prompt")
        self.assertIn("are you busy", calls[0]["user_prompt"])
        self.assertIn("hello", calls[0]["user_prompt"])

        engine.generate_group_reply(
            latest_message="@me help me check this",
            contexts=["group context", "@me help me check this"],
        )
        self.assertEqual(calls[1]["system_prompt"], "group-prompt")
        self.assertIn("@me help me check this", calls[1]["user_prompt"])


class LoggingAndMemoryTests(unittest.TestCase):
    def test_jsonl_event_logger_writes_one_line_per_event(self) -> None:
        temp_dir = ROOT / ".tmp_observability_unit_logs" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        log_path = temp_dir / "runtime.jsonl"
        logger = JsonlEventLogger(path=log_path)

        logger.log_event("message_received", chat_id="alice", chat_type="friend")
        logger.log_event("message_sent", chat_id="alice", chat_type="friend", reply_preview="ok")

        lines = log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        self.assertEqual(first["event_type"], "message_received")
        self.assertEqual(second["event_type"], "message_sent")
        self.assertTrue(first["timestamp"].endswith("Z"))
        self.assertEqual(len(tail_jsonl_events(limit=1, path=log_path)), 1)

    def test_jsonl_event_logger_redacts_sensitive_values_and_rotates(self) -> None:
        temp_dir = ROOT / ".tmp_observability_unit_logs" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        log_path = temp_dir / "runtime.jsonl"
        logger = JsonlEventLogger(path=log_path, max_bytes=120, backup_count=2)

        logger.log_event("prompt_built", prompt_preview="api_key=super-secret-token")
        logger.log_event("prompt_built", prompt_preview="Bearer abcdefghijklmnopqrstuvwxyz")
        logger.log_event("message_sent", reply_preview="token=my-token-value")

        current_text = log_path.read_text(encoding="utf-8")
        self.assertIn("[redacted]", current_text)
        self.assertNotIn("super-secret-token", current_text)
        self.assertNotIn("my-token-value", current_text)
        self.assertTrue((temp_dir / "runtime.jsonl.1").exists())

    def test_memory_store_create_load_and_update_flows(self) -> None:
        temp_dir = ROOT / ".tmp_observability_unit_memory" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        store = MemoryStore(base_dir=temp_dir)

        empty = store.load("friend demo")
        self.assertEqual(empty.chat_id, "friend demo")
        self.assertEqual(empty.summary_text, "")
        self.assertEqual(empty.recent_conversation, [])

        updated = store.update_summary("friend demo", "Prefers short status updates.")
        self.assertEqual(updated.summary_text, "Prefers short status updates.")
        store.append_snapshot("friend demo", ["hi", "are you there?"], captured_at="2026-04-22T10:00:00Z")

        loaded = store.load("friend demo")
        self.assertEqual(loaded.summary_text, "Prefers short status updates.")
        self.assertEqual(len(loaded.recent_conversation), 1)
        self.assertEqual(loaded.recent_conversation[0].messages, ["hi", "are you there?"])
        self.assertEqual(loaded.recent_conversation[0].captured_at, "2026-04-22T10:00:00Z")

    def test_memory_store_truncates_redacts_and_limits_snapshots(self) -> None:
        temp_dir = ROOT / ".tmp_observability_unit_memory" / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        store = MemoryStore(
            base_dir=temp_dir,
            max_snapshots=2,
            max_messages_per_snapshot=2,
            max_chars_per_message=24,
            max_summary_chars=32,
        )

        store.update_summary("friend demo", "api_key=super-secret-value and a very long summary that should be shortened")
        store.append_snapshot("friend demo", ["one", "two", "three token=abcdef"])
        store.append_snapshot("friend demo", ["four", "five"])
        store.append_snapshot("friend demo", ["six", "seven"])

        loaded = store.load("friend demo")
        self.assertIn("[redacted]", loaded.summary_text)
        self.assertNotIn("super-secret-value", loaded.summary_text)
        self.assertLessEqual(len(loaded.summary_text), 32 + len("...(truncated)"))
        self.assertEqual(len(loaded.recent_conversation), 2)
        self.assertEqual(loaded.recent_conversation[0].messages, ["four", "five"])
        self.assertEqual(loaded.recent_conversation[1].messages, ["six", "seven"])


class GlobalAutoReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = import_wechat_runtime_with_stubs()

    def build_app(self):
        return self.runtime.WeChatAIApp(
            engine=types.SimpleNamespace(
                context_limit=10,
                generate_friend_reply=lambda latest_message, contexts: f"reply:{latest_message}",
                generate_group_reply=lambda latest_message, contexts: f"group:{latest_message}",
            ),
            fallback_reply="fallback",
            mention_names=("me",),
        )

    def test_process_unread_session_merges_direct_messages_into_one_reply(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []
        opened_chats: list[str] = []
        fake_main_window = self._build_fake_active_chat([("hello", 1, False), ("there", 2, False)])

        self.runtime.Navigator = types.SimpleNamespace(
            open_dialog_window=lambda friend, is_maximize=False, search_pages=5: opened_chats.append(friend) or fake_main_window
        )
        self.runtime.Tools = types.SimpleNamespace(is_group_chat=lambda window: False)
        self.runtime.Messages = types.SimpleNamespace(
            pull_messages=lambda friend, number, close_weixin=False, search_pages=5: ["earlier-context"],
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        app = self.build_app()
        result = app.process_unread_session("Alice", ["hello", "there"])

        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(opened_chats, ["Alice"])
        self.assertEqual(sent_messages, [("Alice", ["reply:hello\nthere"])])
        self.assertIn("Alice", app.active_last_seen_signature_by_session)

    def test_process_unread_session_ignores_group_messages_without_mention(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []

        self.runtime.Navigator = types.SimpleNamespace(
            open_dialog_window=lambda friend, is_maximize=False, search_pages=5: {"friend": friend}
        )
        self.runtime.Tools = types.SimpleNamespace(is_group_chat=lambda window: True)
        self.runtime.Messages = types.SimpleNamespace(
            pull_messages=lambda friend, number, close_weixin=False, search_pages=5: ["earlier-group-context"],
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        app = self.build_app()
        result = app.process_unread_session("Group", ["hello everyone", "please reply"])

        self.assertEqual(result["group_replies"], 0)
        self.assertEqual(sent_messages, [])

    def test_process_unread_session_replies_to_group_mentions(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []
        fake_main_window = self._build_fake_active_chat([("@me help me", 1, False), ("@鎵€鏈變汉 meeting", 2, False)])

        self.runtime.Navigator = types.SimpleNamespace(
            open_dialog_window=lambda friend, is_maximize=False, search_pages=5: fake_main_window
        )
        self.runtime.Tools = types.SimpleNamespace(is_group_chat=lambda window: True)
        self.runtime.Messages = types.SimpleNamespace(
            pull_messages=lambda friend, number, close_weixin=False, search_pages=5: ["earlier-group-context"],
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        app = self.build_app()
        result = app.process_unread_session("Group", ["@me help me", "@所有人 meeting"])

        self.assertEqual(result["group_replies"], 1)
        self.assertEqual(sent_messages, [("Group", ["group:@me help me\n@所有人 meeting"])])

    def test_process_unread_session_keeps_follow_up_messages_detectable_in_active_chat(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []
        fake_main_window = self._build_fake_active_chat([("hello", 1, False), ("there", 2, False)])
        self.runtime.Navigator = types.SimpleNamespace(
            open_dialog_window=lambda friend, is_maximize=False, search_pages=5: fake_main_window,
            open_weixin=lambda is_maximize=False: fake_main_window,
        )
        self.runtime.Tools = types.SimpleNamespace(
            is_group_chat=lambda window: False,
            activate_chatList=lambda chat_list: None,
            is_my_bubble=lambda window, item: item.mine,
        )
        self.runtime.Messages = types.SimpleNamespace(
            pull_messages=lambda friend, number, close_weixin=False, search_pages=5: ["earlier-context"],
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages)),
        )

        app = self.build_app()
        app.active_merge_window = 3.0

        result = app.process_unread_session("Alice", ["hello", "there"])

        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(sent_messages, [("Alice", ["reply:hello\nthere"])])

        fake_main_window.chat_list = self._build_fake_active_chat(
            [("hello", 1, False), ("there", 2, False), ("reply:hello\nthere", 3, True), ("follow-up", 4, False)]
        ).chat_list

        app.process_active_chat_session(now=1.0)
        follow_up_result = app.process_active_chat_session(now=4.5)

        self.assertEqual(follow_up_result["friend_replies"], 1)
        self.assertEqual(
            sent_messages,
            [("Alice", ["reply:hello\nthere"]), ("Alice", ["reply:follow-up"])],
        )

    def _build_fake_active_chat(self, initial_messages: list[tuple[str, int, bool]]):
        class FakeElementInfo:
            def __init__(self, runtime_id: int) -> None:
                self.runtime_id = runtime_id

        class FakeItem:
            def __init__(self, text: str, runtime_id: int, mine: bool) -> None:
                self._text = text
                self.element_info = FakeElementInfo(runtime_id)
                self.mine = mine

            def window_text(self) -> str:
                return self._text

            def class_name(self) -> str:
                return "mmui::ChatTextItemView"

        class FakeControl:
            def __init__(self, text: str = "", items: list[FakeItem] | None = None) -> None:
                self._text = text
                self._items = items or []

            def exists(self, timeout=0.1) -> bool:
                return True

            def window_text(self) -> str:
                return self._text

            def children(self, control_type=None):
                return self._items

        class FakeMainWindow:
            def __init__(self, messages: list[tuple[str, int, bool]]) -> None:
                self.chat_label = FakeControl(text="Alice")
                self.chat_list = FakeControl(items=[FakeItem(text, runtime_id, mine) for text, runtime_id, mine in messages])

            def child_window(self, **kwargs):
                if kwargs.get("_kind") == "CurrentChatText":
                    return self.chat_label
                if kwargs.get("_kind") == "FriendChatList":
                    return self.chat_list
                raise AssertionError(f"unexpected child_window lookup: {kwargs}")

        return FakeMainWindow(initial_messages)

    def test_process_active_chat_session_bootstraps_existing_messages_without_reply(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []
        fake_main_window = self._build_fake_active_chat([("old-message", 1, False)])
        self.runtime.Navigator = types.SimpleNamespace(open_weixin=lambda is_maximize=False: fake_main_window)
        self.runtime.Tools = types.SimpleNamespace(
            activate_chatList=lambda chat_list: None,
            is_group_chat=lambda window: False,
            is_my_bubble=lambda window, item: item.mine,
        )
        self.runtime.Messages = types.SimpleNamespace(
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        app = self.build_app()
        app.active_merge_window = 3.0
        result = app.process_active_chat_session(now=0.0)

        self.assertEqual(result["friend_replies"], 0)
        self.assertEqual(app.active_pending_messages, [])
        self.assertIn("Alice", app.active_last_seen_signature_by_session)
        self.assertEqual(sent_messages, [])

    def test_process_active_chat_session_merges_only_messages_arriving_after_bootstrap(self) -> None:
        sent_messages: list[tuple[str, list[str]]] = []
        fake_main_window = self._build_fake_active_chat([("old-message", 1, False)])
        self.runtime.Navigator = types.SimpleNamespace(open_weixin=lambda is_maximize=False: fake_main_window)
        self.runtime.Tools = types.SimpleNamespace(
            activate_chatList=lambda chat_list: None,
            is_group_chat=lambda window: False,
            is_my_bubble=lambda window, item: item.mine,
        )
        self.runtime.Messages = types.SimpleNamespace(
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        app = self.build_app()
        app.active_merge_window = 3.0

        app.process_active_chat_session(now=0.0)
        fake_main_window.chat_list = self._build_fake_active_chat([("old-message", 1, False), ("new-message", 2, False)]).chat_list
        app.process_active_chat_session(now=1.0)
        result = app.process_active_chat_session(now=4.5)

        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(sent_messages, [("Alice", ["reply:new-message"])])
        self.assertEqual(app.active_pending_messages, [])

    def test_run_global_auto_reply_polls_and_aggregates_results(self) -> None:
        poll_results = [
            {"Alice": ["hello"], "Group": ["hi all"]},
            {"Group": ["@me help"]},
            {},
        ]

        class FakeMessages:
            def __init__(self, results: list[dict[str, list[str]]]) -> None:
                self.results = results
                self.calls = 0

            def check_new_messages(self, close_weixin=False):
                index = min(self.calls, len(self.results) - 1)
                self.calls += 1
                return self.results[index]

        self.runtime.Messages = FakeMessages(poll_results)
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 2)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: None,
            time=iter([0.0, 0.0, 0.4, 0.8, 1.2, 1.6, 1.9, 2.1, 2.1]).__next__,
        )

        app = self.build_app()

        def fake_unread(self, session_name: str, unread_messages: list[str]) -> dict[str, int]:
            if session_name == "Alice":
                return {"friend_replies": 1, "group_replies": 0, "errors": 0}
            if unread_messages == ["hi all"]:
                return {"friend_replies": 0, "group_replies": 0, "errors": 0}
            return {"friend_replies": 0, "group_replies": 1, "errors": 0}

        original_unread = self.runtime.WeChatAIApp.process_unread_session
        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_unread_session = fake_unread
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {"friend_replies": 0, "group_replies": 0, "errors": 0}
        try:
            result = app.run_global_auto_reply(duration="2s", poll_interval=0.5)
        finally:
            self.runtime.WeChatAIApp.process_unread_session = original_unread
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertEqual(result["polls"], 3)
        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(result["group_replies"], 1)
        self.assertEqual(result["errors"], 0)

    def test_run_global_auto_reply_forever_stops_cleanly_on_keyboard_interrupt(self) -> None:
        class FakeMessages:
            def __init__(self) -> None:
                self.calls = 0

            def check_new_messages(self, close_weixin=False):
                self.calls += 1
                if self.calls >= 2:
                    raise KeyboardInterrupt()
                return {"Alice": ["hello"]}

        self.runtime.Messages = FakeMessages()
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 999)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: None,
            time=iter([0.0, 0.0, 0.5, 1.0]).__next__,
        )

        app = self.build_app()

        original_unread = self.runtime.WeChatAIApp.process_unread_session
        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_unread_session = lambda self, session_name, unread_messages: {
            "friend_replies": 1,
            "group_replies": 0,
            "errors": 0,
        }
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        try:
            result = app.run_global_auto_reply(duration="999s", poll_interval=0.5, forever=True)
        finally:
            self.runtime.WeChatAIApp.process_unread_session = original_unread
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertEqual(result["polls"], 1)
        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(result["errors"], 0)

    def test_run_global_auto_reply_emits_heartbeat_events(self) -> None:
        logged_events: list[dict[str, object]] = []

        class FakeMessages:
            def check_new_messages(self, close_weixin=False):
                return {}

        self.runtime.Messages = FakeMessages()
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 2)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: None,
            time=iter([0.0, 0.0, 0.6, 0.6, 1.2, 1.2, 1.8, 1.8, 2.1, 2.1]).__next__,
        )

        app = self.build_app()
        app.engine.event_logger = types.SimpleNamespace(
            log_event=lambda event_type, **fields: logged_events.append({"event_type": event_type, **fields})
        )

        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        try:
            result = app.run_global_auto_reply(
                duration="2s",
                poll_interval=0.5,
                heartbeat_interval=0.5,
            )
        finally:
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertEqual(result["errors"], 0)
        heartbeat_events = [event for event in logged_events if event["event_type"] == "heartbeat"]
        self.assertGreaterEqual(len(heartbeat_events), 2)

    def test_run_global_auto_reply_retries_after_loop_errors_with_backoff(self) -> None:
        sleep_calls: list[float] = []

        class FakeMessages:
            def __init__(self) -> None:
                self.calls = 0

            def check_new_messages(self, close_weixin=False):
                self.calls += 1
                if self.calls <= 2:
                    raise RuntimeError("ui busy")
                return {"Alice": ["hello"]}

        self.runtime.Messages = FakeMessages()
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 2)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: sleep_calls.append(seconds),
            time=iter([0.0, 0.0, 0.5, 1.0, 1.2, 1.6, 2.1, 2.1]).__next__,
        )

        app = self.build_app()

        original_unread = self.runtime.WeChatAIApp.process_unread_session
        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_unread_session = lambda self, session_name, unread_messages: {
            "friend_replies": 1,
            "group_replies": 0,
            "errors": 0,
        }
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        try:
            result = app.run_global_auto_reply(
                duration="2s",
                poll_interval=0.5,
                error_backoff_seconds=1.0,
            )
        finally:
            self.runtime.WeChatAIApp.process_unread_session = original_unread
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertGreaterEqual(result["errors"], 2)
        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(sleep_calls[:2], [1.0, 2.0])

    def test_run_global_auto_reply_resets_backoff_after_success(self) -> None:
        sleep_calls: list[float] = []

        class FakeMessages:
            def __init__(self) -> None:
                self.calls = 0

            def check_new_messages(self, close_weixin=False):
                self.calls += 1
                if self.calls in (1, 2, 4):
                    raise RuntimeError(f"ui busy {self.calls}")
                return {"Alice": ["hello"]}

        self.runtime.Messages = FakeMessages()
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 3)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: sleep_calls.append(seconds),
            time=iter([0.0, 0.0, 0.5, 1.0, 1.2, 1.6, 2.0, 2.2, 2.6, 3.1, 3.1]).__next__,
        )

        app = self.build_app()

        original_unread = self.runtime.WeChatAIApp.process_unread_session
        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_unread_session = lambda self, session_name, unread_messages: {
            "friend_replies": 1,
            "group_replies": 0,
            "errors": 0,
        }
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        try:
            result = app.run_global_auto_reply(
                duration="3s",
                poll_interval=0.5,
                error_backoff_seconds=1.0,
            )
        finally:
            self.runtime.WeChatAIApp.process_unread_session = original_unread
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertGreaterEqual(result["errors"], 3)
        self.assertEqual(sleep_calls[:4], [1.0, 2.0, 0.5, 1.0])

    def test_run_global_auto_reply_flushes_pending_messages_on_interrupt_and_logs_event(self) -> None:
        logged_events: list[dict[str, object]] = []

        class FakeMessages:
            def __init__(self) -> None:
                self.calls = 0

            def check_new_messages(self, close_weixin=False):
                self.calls += 1
                if self.calls >= 2:
                    raise KeyboardInterrupt()
                return {}

        self.runtime.Messages = FakeMessages()
        self.runtime.Tools = types.SimpleNamespace(match_duration=lambda duration: 999)
        self.runtime.time = types.SimpleNamespace(
            sleep=lambda seconds: None,
            time=iter([0.0, 0.0, 0.5, 1.0]).__next__,
        )

        app = self.build_app()
        app.engine.event_logger = types.SimpleNamespace(
            log_event=lambda event_type, **fields: logged_events.append({"event_type": event_type, **fields})
        )
        app.active_pending_session = "Alice"
        app.active_pending_is_group = False
        app.active_pending_messages = ["buffered-1", "buffered-2"]
        app.active_pending_contexts = ["ctx-1"]
        app.active_pending_deadline = 10.0

        sent_messages: list[tuple[str, list[str]]] = []
        self.runtime.Messages.send_messages_to_friend = lambda friend, messages, close_weixin=False: sent_messages.append(
            (friend, messages)
        )

        original_active = self.runtime.WeChatAIApp.process_active_chat_session
        self.runtime.WeChatAIApp.process_active_chat_session = lambda self, now=None: {
            "friend_replies": 0,
            "group_replies": 0,
            "errors": 0,
        }
        try:
            result = app.run_global_auto_reply(duration="999s", poll_interval=0.5, forever=True)
        finally:
            self.runtime.WeChatAIApp.process_active_chat_session = original_active

        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(sent_messages, [("Alice", ["reply:buffered-1\nbuffered-2"])])
        shutdown_flush_events = [event for event in logged_events if event["event_type"] == "shutdown_flush"]
        self.assertEqual(len(shutdown_flush_events), 1)
        self.assertEqual(shutdown_flush_events[0]["chat_id"], "Alice")


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ReplyEngineTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(LoggingAndMemoryTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(GlobalAutoReplyTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
