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


from wechat_ai.logging_utils import read_jsonl_events  # type: ignore  # noqa: E402
from wechat_ai.memory.memory_store import MemoryStore  # type: ignore  # noqa: E402
from wechat_ai.models import Message  # type: ignore  # noqa: E402
from wechat_ai.orchestration.message_parser import MessageParser  # type: ignore  # noqa: E402
from wechat_ai.orchestration.reply_pipeline import ReplyPipeline, ScenePrompts  # type: ignore  # noqa: E402


def import_wechat_runtime_with_stubs():
    pyautogui_stub = types.ModuleType("pyautogui")
    pyautogui_stub.hotkey = lambda *args, **kwargs: None

    pyweixin_stub = types.ModuleType("pyweixin")
    pyweixin_stub.AutoReply = object()
    pyweixin_stub.Contacts = object()
    pyweixin_stub.GlobalConfig = types.SimpleNamespace(close_weixin=False, search_pages=5)
    pyweixin_stub.Messages = object()
    pyweixin_stub.Navigator = object()
    pyweixin_stub.Tools = object()

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
        for name in (
            "pyautogui",
            "pyweixin",
            "pyweixin.Uielements",
            "pyweixin.WinSettings",
            "wechat_ai.wechat_runtime",
        )
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


class ReplyPipelineOrchestrationTests(unittest.TestCase):
    def test_generate_reply_wires_profiles_context_retrieval_and_scene_engine(self) -> None:
        call_order: list[str] = []
        logged_events: list[dict[str, object]] = []

        class FakeProfileStore:
            def load_user_profile(self, user_id: str):
                call_order.append(f"user:{user_id}")
                return types.SimpleNamespace(user_id=user_id, display_name="Alice")

            def load_agent_profile(self, agent_id: str):
                call_order.append(f"agent:{agent_id}")
                return types.SimpleNamespace(agent_id=agent_id, display_name="Assistant")

        class FakeContextManager:
            def prepare_message(self, message: Message) -> Message:
                call_order.append(f"context:{message.chat_id}")
                return Message(
                    chat_id=message.chat_id,
                    chat_type=message.chat_type,
                    sender_name=message.sender_name,
                    text=message.text,
                    timestamp=message.timestamp,
                    context=["trimmed-1", "trimmed-2"],
                )

        class FakeRetriever:
            def retrieve(self, query: str, limit: int = 3):
                call_order.append(f"retrieval:{query}:{limit}")
                return [
                    types.SimpleNamespace(text="kb-1"),
                    types.SimpleNamespace(text="kb-2"),
                ]

        class FakeReplyEngine:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []
                self.prompt_builder = types.SimpleNamespace(
                    debug_preview=lambda **kwargs: f"prompt::{kwargs['latest_message']}::{kwargs.get('memory_summary', '')}"
                )

            def generate_friend_reply(self, latest_message: str, contexts: list[str], **kwargs: object) -> str:
                call_order.append("engine:friend")
                self.calls.append(
                    {
                        "scene": "friend",
                        "latest_message": latest_message,
                        "contexts": contexts,
                        **kwargs,
                    }
                )
                return "friend-reply"

        class FakeMemoryStore:
            def __init__(self) -> None:
                self.snapshots: list[tuple[str, list[str]]] = []

            def load_summary_text(self, chat_id: str) -> str:
                call_order.append(f"memory:{chat_id}")
                return "Alice prefers concise replies."

            def append_snapshot(self, chat_id: str, messages: list[str]) -> None:
                self.snapshots.append((chat_id, list(messages)))

        memory_store = FakeMemoryStore()

        class FakeLogger:
            def log_event(self, event_type: str, **fields: object) -> None:
                logged_events.append({"event_type": event_type, **fields})

        engine = FakeReplyEngine()
        pipeline = ReplyPipeline(
            provider=object(),
            prompts=ScenePrompts(friend_system_prompt="friend", group_system_prompt="group"),
            context_limit=2,
            model="MiniMax-M2.5",
            profile_store=FakeProfileStore(),
            active_agent_id="assistant-1",
            context_manager=FakeContextManager(),
            retriever=FakeRetriever(),
            reply_engine=engine,
            memory_store=memory_store,
            event_logger=FakeLogger(),
            prompt_preview_max_chars=18,
        )

        reply = pipeline.generate_reply(
            Message(
                chat_id="alice-chat",
                chat_type="friend",
                sender_name="Alice",
                text="hello",
                context=["older", "newer"],
            )
        )

        self.assertEqual(reply, "friend-reply")
        self.assertEqual(
            call_order,
            [
                "user:alice-chat",
                "agent:assistant-1",
                "context:alice-chat",
                "retrieval:hello:3",
                "memory:alice-chat",
                "engine:friend",
            ],
        )
        self.assertEqual(engine.calls[0]["contexts"], ["trimmed-1", "trimmed-2"])
        self.assertEqual(getattr(engine.calls[0]["user_profile"], "user_id"), "alice-chat")
        self.assertEqual(getattr(engine.calls[0]["agent_profile"], "agent_id"), "assistant-1")
        self.assertEqual(engine.calls[0]["knowledge_chunks"], ["kb-1", "kb-2"])
        self.assertEqual(engine.calls[0]["memory_summary"], "Alice prefers concise replies.")
        self.assertEqual(
            memory_store.snapshots,
            [("alice-chat", ["trimmed-1", "trimmed-2", "hello", "friend-reply"])],
        )
        self.assertEqual(
            [event["event_type"] for event in logged_events],
            [
                "message_received",
                "profile_loaded",
                "profile_loaded",
                "retrieval_completed",
                "prompt_built",
                "model_completed",
            ],
        )
        self.assertEqual(logged_events[4]["prompt_preview"], "prompt::hello::Ali...(truncated)")

    def test_generate_reply_accepts_message_like_mapping_for_group_messages(self) -> None:
        class FakeProfileStore:
            def __init__(self) -> None:
                self.user_ids: list[str] = []

            def load_user_profile(self, user_id: str):
                self.user_ids.append(user_id)
                return types.SimpleNamespace(user_id=user_id)

            def load_agent_profile(self, agent_id: str):
                return types.SimpleNamespace(agent_id=agent_id)

        class FakeReplyEngine:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []
                self.prompt_builder = types.SimpleNamespace(debug_preview=lambda **kwargs: "preview")

            def generate_group_reply(self, latest_message: str, contexts: list[str], **kwargs: object) -> str:
                self.calls.append(
                    {
                        "latest_message": latest_message,
                        "contexts": contexts,
                        **kwargs,
                    }
                )
                return "group-reply"

        store = FakeProfileStore()
        engine = FakeReplyEngine()
        pipeline = ReplyPipeline(
            provider=object(),
            prompts=ScenePrompts(friend_system_prompt="friend", group_system_prompt="group"),
            profile_store=store,
            reply_engine=engine,
            active_agent_id="assistant-2",
            retriever=None,
        )

        reply = pipeline.generate_reply(
            {
                "chat_id": "team-room",
                "chat_type": "group",
                "sender_name": "Bob",
                "text": "@bot can you help?",
                "context": ["ctx-1", "ctx-2"],
            }
        )

        self.assertEqual(reply, "group-reply")
        self.assertEqual(store.user_ids, ["Bob"])
        self.assertEqual(engine.calls[0]["contexts"], ["ctx-1", "ctx-2"])
        self.assertEqual(engine.calls[0]["knowledge_chunks"], [])
        self.assertEqual(engine.calls[0]["memory_summary"], None)

    def test_generate_reply_writes_logs_and_updates_memory_store_end_to_end(self) -> None:
        temp_root = ROOT / ".tmp_observability_e2e" / str(uuid4())
        logs_path = temp_root / "runtime.jsonl"
        memory_dir = temp_root / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        store = MemoryStore(base_dir=memory_dir)
        store.update_summary("alice-chat", "User prefers short answers.")

        class FakeProvider:
            def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
                self.system_prompt = system_prompt
                self.user_prompt = user_prompt
                self.model = model
                return "收到，晚点给你同步。"

        provider = FakeProvider()
        pipeline = ReplyPipeline(
            provider=provider,
            prompts=ScenePrompts(friend_system_prompt="friend-system", group_system_prompt="group-system"),
            model="MiniMax-M2.5",
            memory_store=store,
            event_logger=types.SimpleNamespace(
                log_event=lambda event_type, **fields: __import__("wechat_ai.logging_utils", fromlist=["JsonlEventLogger"]).JsonlEventLogger(logs_path).log_event(event_type, **fields)
            ),
        )

        reply = pipeline.generate_reply(
            Message(
                chat_id="alice-chat",
                chat_type="friend",
                sender_name="Alice",
                text="今天先给我一句结论",
                context=["上次我们讨论的是发布计划", "你说今晚会同步状态"],
            )
        )

        self.assertEqual(reply, "收到，晚点给你同步。")
        events = read_jsonl_events(logs_path)
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "message_received",
                "prompt_built",
                "model_completed",
            ],
        )
        record = store.load("alice-chat")
        self.assertEqual(record.summary_text, "User prefers short answers.")
        self.assertEqual(len(record.recent_conversation), 1)
        self.assertEqual(
            record.recent_conversation[0].messages,
            ["上次我们讨论的是发布计划", "你说今晚会同步状态", "今天先给我一句结论", "收到，晚点给你同步。"],
        )


class WeChatRuntimeReplyPipelineWiringTests(unittest.TestCase):
    def test_from_env_passes_profile_and_retrieval_dependencies_into_pipeline(self) -> None:
        runtime = import_wechat_runtime_with_stubs()
        captured: dict[str, object] = {}

        class FakePipeline:
            def __init__(self, provider, prompts, context_limit=10, model=None, **kwargs) -> None:
                captured["provider"] = provider
                captured["prompts"] = prompts
                captured["context_limit"] = context_limit
                captured["model"] = model
                captured.update(kwargs)
                self.context_limit = context_limit

            def generate_reply(self, message: object) -> str:
                return "reply"

            def generate_friend_reply(self, latest_message: str, contexts: list[str]) -> str:
                return "friend-reply"

            def generate_group_reply(self, latest_message: str, contexts: list[str]) -> str:
                return "group-reply"

        runtime.MiniMaxSettings = types.SimpleNamespace(
            from_env=lambda: types.SimpleNamespace(
                api_key="demo-key",
                api_url="https://example.invalid",
                timeout=12,
                model="MiniMax-M2.5",
            )
        )
        runtime.ReplySettings = types.SimpleNamespace(
            from_env=lambda: types.SimpleNamespace(
                friend_system_prompt="friend-prompt",
                group_system_prompt="group-prompt",
                context_limit=7,
                fallback_reply="fallback",
                group_mention_names=("bot",),
                prompt_preview_max_chars=128,
            )
        )
        runtime.ProfileSettings = types.SimpleNamespace(
            from_env=lambda: types.SimpleNamespace(
                default_active_agent_id="assistant-9",
                user_profile_dir=Path("users"),
                agent_profile_dir=Path("agents"),
            )
        )
        runtime.MiniMaxProvider = lambda api_key, api_url, timeout: {
            "api_key": api_key,
            "api_url": api_url,
            "timeout": timeout,
        }
        runtime.ReplyPipeline = FakePipeline
        runtime._build_profile_store = lambda settings: "profile-store"
        runtime._build_retriever = lambda: "retriever"
        runtime._build_memory_store = lambda: "memory-store"
        runtime._build_event_logger = lambda: "event-logger"

        app = runtime.WeChatAIApp.from_env()

        self.assertIsInstance(app.engine, FakePipeline)
        self.assertEqual(captured["context_limit"], 7)
        self.assertEqual(captured["model"], "MiniMax-M2.5")
        self.assertEqual(captured["profile_store"], "profile-store")
        self.assertEqual(captured["retriever"], "retriever")
        self.assertEqual(captured["memory_store"], "memory-store")
        self.assertEqual(captured["event_logger"], "event-logger")
        self.assertEqual(captured["prompt_preview_max_chars"], 128)
        self.assertEqual(captured["active_agent_id"], "assistant-9")

    def test_send_reply_uses_single_generate_reply_entrypoint_and_preserves_fallback_in_callbacks(self) -> None:
        runtime = import_wechat_runtime_with_stubs()

        sent_messages: list[tuple[str, list[str]]] = []
        logged_events: list[dict[str, object]] = []
        runtime.Messages = types.SimpleNamespace(
            send_messages_to_friend=lambda friend, messages, close_weixin=False: sent_messages.append((friend, messages))
        )

        class FakeEngine:
            context_limit = 5

            def __init__(self) -> None:
                self.messages: list[object] = []
                self.raise_on_generate = False
                self.event_logger = types.SimpleNamespace(
                    log_event=lambda event_type, **fields: logged_events.append({"event_type": event_type, **fields})
                )

            def generate_reply(self, message: object) -> str:
                if self.raise_on_generate:
                    raise RuntimeError("provider down")
                self.messages.append(message)
                return "pipeline-reply"

        engine = FakeEngine()
        app = runtime.WeChatAIApp(
            engine=engine,
            fallback_reply="fallback",
            mention_names=("bot",),
        )

        result = app._send_reply(
            session_name="Alice",
            message_text="hello",
            contexts=["c1", "c2"],
            is_group=False,
        )

        self.assertEqual(result["friend_replies"], 1)
        self.assertEqual(sent_messages, [("Alice", ["pipeline-reply"])])
        self.assertEqual(len(engine.messages), 1)
        message = engine.messages[0]
        self.assertEqual(message.chat_id, "Alice")
        self.assertEqual(message.chat_type, "friend")
        self.assertEqual(message.context, ["c1", "c2"])
        self.assertEqual(logged_events[0]["event_type"], "message_sent")
        engine.raise_on_generate = True
        self.assertEqual(app.friend_callback("hello", ["c1"]), "fallback")
        self.assertEqual(logged_events[-1]["event_type"], "fallback_used")

    def test_friend_and_group_callbacks_accept_real_session_identifiers(self) -> None:
        runtime = import_wechat_runtime_with_stubs()

        class FakeEngine:
            def __init__(self) -> None:
                self.messages: list[object] = []

            def generate_reply(self, message: object) -> str:
                self.messages.append(message)
                return "ok"

        engine = FakeEngine()
        app = runtime.WeChatAIApp(
            engine=engine,
            fallback_reply="fallback",
            mention_names=("bot",),
        )

        friend_reply = app.friend_callback("hello", ["ctx"], chat_id="Alice")
        group_reply = app.group_callback(
            "@bot hi",
            ["ctx"],
            chat_id="Project Group",
            sender_name="Bob",
        )

        self.assertEqual(friend_reply, "ok")
        self.assertEqual(group_reply, "ok")
        self.assertEqual(engine.messages[0].chat_id, "Alice")
        self.assertEqual(engine.messages[0].sender_name, "Alice")
        self.assertEqual(engine.messages[1].chat_id, "Project Group")
        self.assertEqual(engine.messages[1].sender_name, "Bob")

    def test_group_callback_normalizes_blank_sender_name_to_chat_id(self) -> None:
        runtime = import_wechat_runtime_with_stubs()

        class FakeEngine:
            def __init__(self) -> None:
                self.messages: list[object] = []

            def generate_reply(self, message: object) -> str:
                self.messages.append(message)
                return "ok"

        engine = FakeEngine()
        app = runtime.WeChatAIApp(
            engine=engine,
            fallback_reply="fallback",
            mention_names=("bot",),
        )

        group_reply = app.group_callback(
            "@bot hi",
            ["ctx"],
            chat_id="Project Group",
            sender_name="   ",
        )

        self.assertEqual(group_reply, "ok")
        self.assertEqual(engine.messages[0].chat_id, "Project Group")
        self.assertEqual(engine.messages[0].sender_name, "Project Group")

    def test_run_group_at_auto_reply_uses_parsed_group_sender_name(self) -> None:
        runtime = import_wechat_runtime_with_stubs()

        class FakeItem:
            def __init__(self, runtime_id: int, text: str) -> None:
                self.element_info = types.SimpleNamespace(runtime_id=runtime_id)
                self._text = text

            def class_name(self) -> str:
                return "mmui::ChatTextItemView"

            def window_text(self) -> str:
                return self._text

        class FakeChatList:
            def __init__(self, items: list[FakeItem]) -> None:
                self._items = list(items)
                self._calls = 0

            def children(self, control_type: str | None = None) -> list[FakeItem]:
                self._calls += 1
                if self._calls >= 3:
                    self._items = [FakeItem(1, "older"), FakeItem(2, "@bot hi")]
                return list(self._items)

        class FakeInputEdit:
            def click_input(self) -> None:
                return None

        class FakeWindow:
            def __init__(self, chat_list: FakeChatList, input_edit: FakeInputEdit) -> None:
                self._chat_list = chat_list
                self._input_edit = input_edit
                self.closed = False

            def child_window(self, **kwargs):
                kind = kwargs.get("_kind")
                if kind == "FriendChatList":
                    return self._chat_list
                if kind == "InputEdit":
                    return self._input_edit
                raise AssertionError(f"unexpected child window lookup: {kwargs}")

            def close(self) -> None:
                self.closed = True

        class FakeEngine:
            def __init__(self) -> None:
                self.messages: list[object] = []

            def generate_reply(self, message: object) -> str:
                self.messages.append(message)
                return "ok"

        chat_list = FakeChatList(items=[FakeItem(1, "older")])
        input_edit = FakeInputEdit()
        main_window = FakeWindow(chat_list=chat_list, input_edit=input_edit)
        engine = FakeEngine()
        app = runtime.WeChatAIApp(
            engine=engine,
            fallback_reply="fallback",
            mention_names=("bot",),
        )

        runtime.Navigator = types.SimpleNamespace(open_dialog_window=lambda **kwargs: main_window)
        runtime.GlobalConfig = types.SimpleNamespace(close_weixin=False, search_pages=5)
        runtime.SystemSettings = types.SimpleNamespace(
            open_listening_mode=lambda **kwargs: None,
            close_listening_mode=lambda: None,
            copy_text_to_clipboard=lambda text: None,
        )
        runtime.Tools = types.SimpleNamespace(
            is_group_chat=lambda window: True,
            activate_chatList=lambda chat_list: None,
            match_duration=lambda value: 1,
            is_my_bubble=lambda window, item: False,
            parse_message_content=lambda ListItem, friendtype: ("  Bob  ", "@bot hi", "text"),
        )
        tick_values = iter([100.0, 100.0, 102.0])
        runtime.time = types.SimpleNamespace(time=lambda: next(tick_values))

        result = app.run_group_at_auto_reply(group_name="Project Group", duration="1s")

        self.assertEqual(result, {"group": "Project Group", "replies_sent": 1})
        self.assertTrue(main_window.closed)
        self.assertEqual(len(engine.messages), 1)
        self.assertEqual(engine.messages[0].chat_id, "Project Group")
        self.assertEqual(engine.messages[0].sender_name, "Bob")


class MessageParserNormalizationTests(unittest.TestCase):
    def test_parse_group_message_normalizes_blank_sender_name_to_chat_id(self) -> None:
        message = MessageParser.parse_group_message(
            chat_id="  Team Room  ",
            sender_name="   ",
            text="  @bot hi  ",
            contexts=["  one  ", "   ", " two "],
        )

        self.assertEqual(message.chat_id, "Team Room")
        self.assertEqual(message.sender_name, "Team Room")
        self.assertEqual(message.text, "@bot hi")
        self.assertEqual(message.context, ["one", "two"])


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ReplyPipelineOrchestrationTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(WeChatRuntimeReplyPipelineWiringTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(MessageParserNormalizationTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
