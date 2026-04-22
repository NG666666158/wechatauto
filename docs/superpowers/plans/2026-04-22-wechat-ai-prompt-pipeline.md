# WeChat AI Prompt Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current simple prompt assembly with a structured reply pipeline that combines user profiles, agent profiles, message context, and retrieved knowledge.

**Architecture:** Build a dedicated orchestration layer under `wechat_ai/orchestration` and keep `wechat_runtime` focused on event detection and transport. Make prompt building deterministic and inspectable so future providers or routing strategies can reuse the same assembly logic.

**Tech Stack:** Python dataclasses, existing MiniMax provider, local RAG layer, unittest regression coverage.

---

### Task 1: Add Message Parsing And Context Management Helpers

**Files:**
- Create: `wechat_ai/orchestration/message_parser.py`
- Create: `wechat_ai/orchestration/context_manager.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Normalize runtime message inputs into shared `Message` objects.
- [ ] Move context truncation concerns out of `reply_engine.py` into a dedicated context manager that can later support summaries.
- [ ] Add tests for:
  - friend message normalization
  - group message normalization
  - max-context truncation
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "refactor: add message and context helpers"`

### Task 2: Add Prompt Builder

**Files:**
- Create: `wechat_ai/orchestration/prompt_builder.py`
- Modify: `wechat_ai/reply_engine.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Implement a `PromptBuilder` that renders these sections in order:
  - agent profile summary
  - user profile summary
  - recent conversation context
  - retrieved knowledge
  - current reply task
- [ ] Add a debug preview method returning the fully rendered prompt as text.
- [ ] Refactor `ReplyEngine` to delegate user-prompt construction to the builder.
- [ ] Add tests that verify section inclusion and ordering.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add structured prompt builder"`

### Task 3: Implement End-To-End Reply Pipeline

**Files:**
- Modify: `wechat_ai/orchestration/reply_pipeline.py`
- Modify: `wechat_ai/wechat_runtime.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Expand the compatibility layer into a real `ReplyPipeline` with a single entrypoint:

```python
def generate_reply(message: Message) -> str:
    ...
```

- [ ] Inside the pipeline:
  - resolve user profile
  - resolve active agent profile
  - gather recent context
  - run retrieval
  - build prompts
  - call the provider
- [ ] Keep fallback handling in `wechat_runtime.py`, not inside the pipeline.
- [ ] Add tests that stub each collaborator and verify call order plus generated reply output.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add reply orchestration pipeline"`

### Task 4: Preserve Current Entry Scripts While Upgrading Behavior

**Files:**
- Modify: `scripts/run_minimax_friend_auto_reply.py`
- Modify: `scripts/run_minimax_group_at_reply.py`
- Modify: `scripts/run_minimax_global_auto_reply.py`
- Modify: `README.md`

- [ ] Keep CLI flags unchanged where possible.
- [ ] Add optional `--debug` support to the friend and group scripts for parity with global mode.
- [ ] Update README examples to describe that replies now include profile and knowledge context when configured.
- [ ] Run:

```powershell
py -3 scripts\run_minimax_global_auto_reply.py --duration 2s --debug
```

- [ ] Expected: startup completes and debug mode prints pipeline-related markers without changing CLI compatibility.
- [ ] Commit: `git commit -m "feat: wire pipeline into runtime entrypoints"`

### Task 5: Add Prompt Preview Smoke Tests

**Files:**
- Create: `scripts/test_prompt_preview.py`
- Modify: `README.md`

- [ ] Add a local script that builds a synthetic message, user profile, agent profile, and retrieved knowledge set, then prints prompt previews without touching WeChat.
- [ ] Use this script as the operator-facing sanity check before troubleshooting live auto-reply behavior.
- [ ] Document the script in README.
- [ ] Run:

```powershell
py -3 scripts\test_prompt_preview.py
```

- [ ] Expected: prompt text preview with all major sections rendered.
- [ ] Commit: `git commit -m "test: add prompt preview smoke script"`
