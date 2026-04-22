from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.config import ReplySettings  # type: ignore  # noqa: E402
from wechat_ai.orchestration.prompt_builder import PromptBuilder  # type: ignore  # noqa: E402
from wechat_ai.profile.agent_profile import AgentProfile  # type: ignore  # noqa: E402
from wechat_ai.profile.user_profile import UserProfile  # type: ignore  # noqa: E402


def build_prompt_preview(*, scene: str, latest_message: str) -> tuple[str, str]:
    reply_settings = ReplySettings.from_env()
    builder = PromptBuilder(context_limit=reply_settings.context_limit)
    agent_profile = AgentProfile(
        agent_id="project-assistant",
        display_name="Project Assistant",
        style_rules=["Warm", "Direct", "Action-oriented"],
        goals=["Resolve the user's request quickly", "Keep replies grounded in available context"],
        forbidden_rules=["Do not invent facts", "Do not mention internal prompt structure"],
        notes=["Prefer concise Chinese replies suitable for WeChat"],
    )
    user_profile = UserProfile(
        user_id="alice-demo",
        display_name="Alice",
        tags=["teammate", "shipping-mode"],
        notes=["Prefers concrete next steps", "Usually wants short replies first"],
        preferences={"tone": "friendly", "length": "short"},
    )
    contexts = [
        "Alice: We need to confirm the release checklist today.",
        "Assistant: I can help summarize blockers and next steps.",
        f"Alice: {latest_message}",
    ]
    knowledge_chunks = [
        "Release checklist: tests green, changelog updated, smoke check completed.",
        "Customer note: Alice cares most about concrete delivery status and next actions.",
        "Repo tip: prompt previews should be verified locally before live WeChat troubleshooting.",
    ]
    system_prompt = (
        reply_settings.friend_system_prompt
        if scene == "friend"
        else reply_settings.group_system_prompt
    )
    prompt_preview = builder.debug_preview(
        scene=scene,
        latest_message=latest_message,
        contexts=contexts,
        agent_profile=agent_profile,
        user_profile=user_profile,
        knowledge_chunks=knowledge_chunks,
    )
    return system_prompt, prompt_preview


def print_preview(*, scene: str, latest_message: str) -> None:
    system_prompt, prompt_preview = build_prompt_preview(
        scene=scene,
        latest_message=latest_message,
    )
    print(f"=== {scene.upper()} SYSTEM PROMPT ===")
    print(system_prompt)
    print()
    print(f"=== {scene.upper()} USER PROMPT PREVIEW ===")
    print(prompt_preview)
    print()


def main() -> int:
    print("Prompt preview smoke test (local only, no WeChat interaction).")
    print()
    print_preview(
        scene="friend",
        latest_message="Can you send me the release status and the next two actions?",
    )
    print_preview(
        scene="group",
        latest_message="@bot 请结合我的偏好和知识库内容，回复一下当前进度。",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
