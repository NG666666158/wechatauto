# WeChat AI Profiles And Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user profile, agent profile, and centralized runtime configuration so replies can become persona-aware without breaking the current MiniMax-based flows.

**Architecture:** Store both user and agent profiles as local JSON documents under `wechat_ai/data`. Build small store classes with predictable load/save semantics, then thread profile summaries into the runtime as optional prompt inputs while preserving current fallback behavior.

**Tech Stack:** Python dataclasses, JSON file storage, existing `wechat_ai.config`, unittest fixtures.

---

### Task 1: Define Profile Models

**Files:**
- Create: `wechat_ai/profile/user_profile.py`
- Create: `wechat_ai/profile/agent_profile.py`
- Modify: `wechat_ai/models.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Define `UserProfile` and `AgentProfile` dataclasses with explicit defaults for tags, notes, preferences, style rules, goals, and forbidden rules.
- [ ] Keep the models serializable with `dataclasses.asdict`.
- [ ] Add unit tests for default construction and round-trip serialization.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add profile models"`

### Task 2: Implement File-Backed Profile Stores

**Files:**
- Create: `wechat_ai/profile/profile_store.py`
- Create: `wechat_ai/profile/tag_manager.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Implement a `ProfileStore` with:
  - `load_user_profile(user_id: str) -> UserProfile`
  - `save_user_profile(profile: UserProfile) -> None`
  - `load_agent_profile(agent_id: str) -> AgentProfile`
  - `save_agent_profile(profile: AgentProfile) -> None`
- [ ] When a profile file is missing, create and return a sensible default object instead of throwing.
- [ ] Add a small `TagManager.normalize(tags: list[str]) -> list[str]` helper that trims, deduplicates, and preserves order.
- [ ] Add tests using temporary directories to verify file creation and reload behavior.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add profile stores"`

### Task 3: Extend Centralized Runtime Settings

**Files:**
- Modify: `wechat_ai/config.py`
- Create: `wechat_ai/profile/defaults.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Add configuration fields for:
  - default active agent id
  - user profile directory override
  - agent profile directory override
  - profile auto-create toggle
- [ ] Move hard-coded default friend/group prompts into profile defaults so runtime prompt behavior can be driven by the active agent profile.
- [ ] Add tests that verify env overrides and defaults resolve correctly.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "refactor: centralize profile runtime settings"`

### Task 4: Thread Profiles Into WeChat Runtime

**Files:**
- Modify: `wechat_ai/wechat_runtime.py`
- Modify: `wechat_ai/reply_engine.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Add helpers on `WeChatAIApp` to resolve:
  - the active agent profile
  - the current user profile for a session name
- [ ] Pass compact profile summaries into reply generation instead of only raw message context.
- [ ] Keep the public callback signatures stable by enriching prompt construction internally.
- [ ] Add tests that verify:
  - direct messages can read a user profile
  - missing profiles do not crash
  - the generated prompt includes agent and user summary text
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: use profiles in reply generation"`

### Task 5: Add Operator Scripts For Profile Management

**Files:**
- Create: `scripts/set_user_profile.py`
- Create: `scripts/set_agent_profile.py`
- Modify: `README.md`

- [ ] Add CLI scripts that accept JSON file input or command-line overrides for basic fields.
- [ ] Print the saved profile JSON after each update so operators can verify the result immediately.
- [ ] Document both scripts in `README.md` with copy-paste examples.
- [ ] Run:

```powershell
py -3 scripts\set_agent_profile.py --agent-id default_assistant
py -3 scripts\set_user_profile.py --user-id friend_demo
```

- [ ] Expected: JSON output for the stored profile files.
- [ ] Commit: `git commit -m "feat: add profile management scripts"`
