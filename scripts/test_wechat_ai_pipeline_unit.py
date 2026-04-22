from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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


class ReplyPipelineCompatibilityTests(unittest.TestCase):
    def test_pipeline_delegates_to_reply_engine_behavior(self) -> None:
        from wechat_ai.orchestration.reply_pipeline import ReplyPipeline, ScenePrompts

        calls: list[dict[str, str | None]] = []

        class FakeProvider:
            def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
                calls.append(
                    {
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "model": model,
                    }
                )
                return "pipeline-output"

        pipeline = ReplyPipeline(
            provider=FakeProvider(),
            prompts=ScenePrompts(
                friend_system_prompt="friend-prompt",
                group_system_prompt="group-prompt",
            ),
            context_limit=3,
            model="MiniMax-M2.5",
        )

        friend_reply = pipeline.generate_friend_reply(
            latest_message="latest friend",
            contexts=["ctx-1", "ctx-2", "ctx-3", "ctx-4"],
        )
        group_reply = pipeline.generate_group_reply(
            latest_message="@me latest group",
            contexts=["group-ctx", "@me latest group"],
        )

        self.assertEqual(friend_reply, "pipeline-output")
        self.assertEqual(group_reply, "pipeline-output")
        self.assertEqual(calls[0]["system_prompt"], "friend-prompt")
        self.assertEqual(calls[0]["model"], "MiniMax-M2.5")
        self.assertIn("latest friend", str(calls[0]["user_prompt"]))
        self.assertIn("ctx-4", str(calls[0]["user_prompt"]))
        self.assertNotIn("ctx-1", str(calls[0]["user_prompt"]))
        self.assertEqual(calls[1]["system_prompt"], "group-prompt")
        self.assertIn("@me latest group", str(calls[1]["user_prompt"]))

    def test_pipeline_keeps_reply_engine_public_api_compatible(self) -> None:
        from wechat_ai.orchestration.reply_pipeline import ReplyPipeline, ScenePrompts

        class FakeProvider:
            def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
                return f"{system_prompt}|{model}|{len(user_prompt)}"

        pipeline = ReplyPipeline(
            provider=FakeProvider(),
            prompts=ScenePrompts(
                friend_system_prompt="friend-prompt",
                group_system_prompt="group-prompt",
            ),
            context_limit=2,
            model=None,
        )

        self.assertIsInstance(pipeline.generate_friend_reply("hello", ["a", "b"]), str)
        self.assertIsInstance(pipeline.generate_group_reply("@me hi", ["a", "b"]), str)
        self.assertEqual(pipeline.context_limit, 2)
        self.assertEqual(pipeline.prompts.friend_system_prompt, "friend-prompt")


class WeChatRuntimePipelineWiringTests(unittest.TestCase):
    def test_from_env_builds_pipeline_from_reply_settings(self) -> None:
        runtime = import_wechat_runtime_with_stubs()

        captured: dict[str, object] = {}

        class FakePipeline:
            def __init__(self, provider, prompts, context_limit: int = 10, model: str | None = None) -> None:
                captured["provider"] = provider
                captured["prompts"] = prompts
                captured["context_limit"] = context_limit
                captured["model"] = model
                self.context_limit = context_limit

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
            )
        )
        runtime.MiniMaxProvider = lambda api_key, api_url, timeout: {
            "api_key": api_key,
            "api_url": api_url,
            "timeout": timeout,
        }
        runtime.ReplyPipeline = FakePipeline

        app = runtime.WeChatAIApp.from_env()

        self.assertIsInstance(app.engine, FakePipeline)
        self.assertEqual(captured["context_limit"], 7)
        self.assertEqual(captured["model"], "MiniMax-M2.5")
        prompts = captured["prompts"]
        self.assertEqual(prompts.friend_system_prompt, "friend-prompt")
        self.assertEqual(prompts.group_system_prompt, "group-prompt")
        self.assertEqual(app.fallback_reply, "fallback")
        self.assertEqual(app.mention_names, ("bot",))


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ReplyPipelineCompatibilityTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(WeChatRuntimePipelineWiringTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
