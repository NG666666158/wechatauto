from __future__ import annotations

import json
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODELS_PATH = ROOT / "wechat_ai" / "models.py"
MESSAGE_PARSER_PATH = ROOT / "wechat_ai" / "orchestration" / "message_parser.py"
CONTEXT_MANAGER_PATH = ROOT / "wechat_ai" / "orchestration" / "context_manager.py"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


models_module = load_module("wechat_ai_models_for_context_tests", MODELS_PATH)
wechat_ai_package = types.ModuleType("wechat_ai")
wechat_ai_package.__path__ = [str(ROOT / "wechat_ai")]
sys.modules.setdefault("wechat_ai", wechat_ai_package)
sys.modules["wechat_ai.models"] = models_module
message_parser_module = load_module("wechat_ai_message_parser_for_context_tests", MESSAGE_PARSER_PATH)
context_manager_module = load_module("wechat_ai_context_manager_for_context_tests", CONTEXT_MANAGER_PATH)

Message = models_module.Message
MessageParser = message_parser_module.MessageParser
ContextManager = context_manager_module.ContextManager


class MessageParserTests(unittest.TestCase):
    def test_friend_message_normalization(self) -> None:
        message = MessageParser.parse_friend_message(
            chat_id="Alice",
            text="  hello there  ",
            contexts=[" earlier note ", "", "  latest note  "],
        )

        self.assertEqual(
            message,
            Message(
                chat_id="Alice",
                chat_type="friend",
                sender_name="Alice",
                text="hello there",
                context=["earlier note", "latest note"],
            ),
        )

    def test_group_message_normalization(self) -> None:
        message = MessageParser.parse_group_message(
            chat_id="Study Group",
            sender_name="Bob",
            text="  @bot can you help?  ",
            contexts=[" Alice: hi team ", "  ", " Bob: @bot can you help? "],
        )

        self.assertEqual(
            message,
            Message(
                chat_id="Study Group",
                chat_type="group",
                sender_name="Bob",
                text="@bot can you help?",
                context=["Alice: hi team", "Bob: @bot can you help?"],
            ),
        )


class ContextManagerTests(unittest.TestCase):
    def test_prepare_message_truncates_to_max_context(self) -> None:
        original = Message(
            chat_id="Alice",
            chat_type="friend",
            sender_name="Alice",
            text="latest",
            context=["msg-1", "msg-2", "msg-3", "msg-4", "msg-5"],
        )

        prepared = ContextManager(max_messages=3).prepare_message(original)

        self.assertEqual(prepared.context, ["msg-3", "msg-4", "msg-5"])
        self.assertEqual(original.context, ["msg-1", "msg-2", "msg-3", "msg-4", "msg-5"])


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(MessageParserTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ContextManagerTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"ok": result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
