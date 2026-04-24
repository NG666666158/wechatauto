from __future__ import annotations

import sys
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeElement:
    def __init__(
        self,
        text: str = "",
        *,
        mine: bool = False,
        runtime_id: int = 1,
        exists: bool = True,
        enabled: bool = True,
    ) -> None:
        self._text = text
        self.mine = mine
        self._exists = exists
        self._enabled = enabled
        self.element_info = type("ElementInfo", (), {"runtime_id": runtime_id})()

    def window_text(self) -> str:
        return self._text

    def exists(self, timeout: float | None = None) -> bool:
        return self._exists

    def is_enabled(self) -> bool:
        return self._enabled


class FakeList:
    def __init__(self, items: list[FakeElement]) -> None:
        self.items = items

    def children(self, control_type: str | None = None) -> list[FakeElement]:
        if control_type == "ListItem":
            return list(self.items)
        return []


class FakeWindow:
    def __init__(
        self,
        *,
        chat_label: str = "Alice",
        messages: list[FakeElement] | None = None,
        minimized: bool = False,
        exists: bool = True,
        input_exists: bool = True,
        input_enabled: bool = True,
    ) -> None:
        self.chat_label = chat_label
        self.chat_list = FakeList(messages or [])
        self.input_edit = FakeElement("", exists=input_exists, enabled=input_enabled)
        self.minimized = minimized
        self._exists = exists

    def exists(self, timeout: float | None = None) -> bool:
        return self._exists

    def is_minimized(self) -> bool:
        return self.minimized

    def child_window(self, **kwargs):
        marker = kwargs.get("_kind")
        if marker == "CurrentChatText":
            return FakeElement(self.chat_label)
        if marker == "FriendChatList":
            return self.chat_list
        if marker == "InputEdit":
            return self.input_edit
        raise AssertionError(f"unexpected lookup: {kwargs}")


class FakeNavigator:
    def __init__(self, window: FakeWindow) -> None:
        self.window = window

    def open_weixin(self, is_maximize: bool = False):
        return self.window


class FakeTools:
    @staticmethod
    def is_my_bubble(window, item) -> bool:
        return bool(getattr(item, "mine", False))


def build_probe(window: FakeWindow):
    from wechat_ai.app.wechat_window_probe import WeChatWindowProbe

    return WeChatWindowProbe(
        navigator=FakeNavigator(window),
        tools=FakeTools(),
        lists=type("Lists", (), {"FriendChatList": {"_kind": "FriendChatList"}})(),
        edits=type("Edits", (), {"InputEdit": {"_kind": "InputEdit"}})(),
        texts=type("Texts", (), {"CurrentChatText": {"_kind": "CurrentChatText"}})(),
    )


class WeChatWindowProbeTests(TestCase):
    def test_probe_reports_ready_when_main_window_chat_list_and_input_are_visible(self) -> None:
        window = FakeWindow(messages=[FakeElement("hello", runtime_id=1), FakeElement("sent", mine=True, runtime_id=2)])
        probe = build_probe(window)

        result = probe.probe_ui_ready()

        self.assertTrue(result.ready)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.current_chat, "Alice")
        self.assertEqual(result.visible_message_count, 2)
        self.assertEqual(result.latest_visible_text, "sent")
        self.assertTrue(result.input_ready)
        self.assertTrue(result.window_ready)
        self.assertTrue(result.current_chat_ready)
        self.assertTrue(result.chat_list_ready)
        self.assertFalse(result.window_minimized)
        self.assertEqual(result.focus_recommendation, "")

    def test_probe_reports_minimized_or_missing_input_as_not_ready(self) -> None:
        window = FakeWindow(
            chat_label="Alice",
            messages=[FakeElement("hello", runtime_id=1)],
            minimized=True,
            input_exists=False,
        )
        probe = build_probe(window)

        result = probe.probe_ui_ready()

        self.assertFalse(result.ready)
        self.assertEqual(result.status, "warn")
        self.assertTrue(result.window_minimized)
        self.assertFalse(result.input_ready)
        self.assertIn("restore_window", result.focus_recommendation)
        self.assertIn("focus_input", result.focus_recommendation)

    def test_visual_confirmer_matches_recent_outgoing_bubble_text(self) -> None:
        from wechat_ai.app.wechat_window_probe import PyWeixinVisualSendConfirmer

        window = FakeWindow(messages=[FakeElement("previous", runtime_id=1), FakeElement("confirmed reply", mine=True, runtime_id=2)])
        confirmer = PyWeixinVisualSendConfirmer(probe=build_probe(window))

        confirmed = confirmer.confirm_sent(conversation_id="friend:Alice", text="confirmed reply")

        self.assertTrue(confirmed)

    def test_visual_confirmer_rejects_when_text_is_not_visible(self) -> None:
        from wechat_ai.app.wechat_window_probe import PyWeixinVisualSendConfirmer

        window = FakeWindow(messages=[FakeElement("other content", mine=True, runtime_id=1)])
        confirmer = PyWeixinVisualSendConfirmer(probe=build_probe(window))

        confirmed = confirmer.confirm_sent(conversation_id="friend:Alice", text="confirmed reply")

        self.assertFalse(confirmed)


if __name__ == "__main__":
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WeChatWindowProbeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
