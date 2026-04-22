# WeChat AI Observability And Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured logs, prompt traceability, and lightweight memory summaries so the enhanced auto-reply pipeline can be debugged and improved safely.

**Architecture:** Keep observability append-only and file-backed for MVP. Separate runtime event logs from longer-lived memory summaries so operational debugging and conversational memory can evolve at different speeds.

**Tech Stack:** JSONL log files, local JSON memory summaries, existing `wechat_ai` pipeline, unittest and smoke scripts.

---

### Task 1: Add Structured Logging Primitives

**Files:**
- Create: `wechat_ai/logging_utils.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Add helpers for JSONL append logging with UTC timestamps and event types.
- [ ] Define event shapes for:
  - message_received
  - profile_loaded
  - retrieval_completed
  - prompt_built
  - model_completed
  - fallback_used
  - message_sent
- [ ] Add tests that write logs to a temporary file and validate one-line-per-event output.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add structured runtime logging"`

### Task 2: Add Pipeline-Level Debug Events

**Files:**
- Modify: `wechat_ai/orchestration/reply_pipeline.py`
- Modify: `wechat_ai/wechat_runtime.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Emit structured events at each major pipeline stage without leaking secrets such as raw API keys.
- [ ] Log prompt previews in truncated form with configurable maximum length.
- [ ] Ensure fallback replies log the underlying exception type and message.
- [ ] Add tests that verify debug events are emitted when a fake logger is injected.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add reply pipeline debug events"`

### Task 3: Add Lightweight Memory Store

**Files:**
- Create: `wechat_ai/memory/conversation_memory.py`
- Create: `wechat_ai/memory/summary_memory.py`
- Create: `wechat_ai/memory/memory_store.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Add a file-backed memory store keyed by `chat_id`.
- [ ] Support:
  - recent conversation snapshots
  - long-term summary text
  - last-updated timestamp
- [ ] Keep summary generation manual or placeholder-driven in MVP; do not add autonomous updating logic yet.
- [ ] Add tests for create/load/update flows.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add lightweight memory store"`

### Task 4: Feed Memory Summary Into Prompt Assembly

**Files:**
- Modify: `wechat_ai/orchestration/prompt_builder.py`
- Modify: `wechat_ai/orchestration/reply_pipeline.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Extend prompt rendering so a memory summary section is included only when present and non-empty.
- [ ] Keep memory summary lower priority than current context and retrieved knowledge.
- [ ] Add tests showing memory summary appears in prompt previews and does not replace recent messages.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "feat: add memory summaries to prompt builder"`

### Task 5: Add Operator Scripts For Logs And Memory Inspection

**Files:**
- Create: `scripts/show_recent_logs.py`
- Create: `scripts/show_memory_summary.py`
- Modify: `README.md`

- [ ] Add a log-inspection script that prints the last N structured events for quick debugging.
- [ ] Add a memory-inspection script that prints the stored summary for a given `chat_id`.
- [ ] Document both scripts in README as the first troubleshooting step after `--debug`.
- [ ] Run:

```powershell
py -3 scripts\show_recent_logs.py --limit 20
py -3 scripts\show_memory_summary.py --chat-id friend_demo
```

- [ ] Expected: readable JSON or text output without requiring a live WeChat session.
- [ ] Commit: `git commit -m "feat: add runtime inspection scripts"`
