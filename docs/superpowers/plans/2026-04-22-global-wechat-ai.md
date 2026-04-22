# Global WeChat AI Auto Reply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a global polling auto-reply entrypoint for `pyweixin` that replies to all unread direct messages and group messages that mention the current user.

**Architecture:** Extend `WeChatAIApp` with a polling coordinator that reads unread sessions from `pyweixin`, classifies sessions with existing window helpers, generates replies with the current AI engine, and sends replies through the existing message sender. Keep state in memory and avoid changing core `pyweixin` behavior.

**Tech Stack:** Python, pyweixin, unittest

---

### Task 1: Add Failing Coordinator Tests

**Files:**
- Modify: `scripts/test_wechat_ai_unit.py`

- [ ] **Step 1: Write failing tests for global polling behavior**
- [ ] **Step 2: Run the unit test file and verify the new tests fail for missing behavior**
- [ ] **Step 3: Implement the minimal runtime changes**
- [ ] **Step 4: Re-run the unit test file and verify it passes**

### Task 2: Implement Global Polling Runtime

**Files:**
- Modify: `wechat_ai/wechat_runtime.py`

- [ ] **Step 1: Add a helper that classifies a session and processes unread messages**
- [ ] **Step 2: Add a global polling loop entrypoint on `WeChatAIApp`**
- [ ] **Step 3: Keep minimal stats so the end-to-end run is observable**
- [ ] **Step 4: Re-run unit tests**

### Task 3: Add a Runnable Entry Script

**Files:**
- Create: `scripts/run_minimax_global_auto_reply.py`

- [ ] **Step 1: Add a CLI script that loads env config and starts the polling runtime**
- [ ] **Step 2: Support duration and poll interval arguments**
- [ ] **Step 3: Print JSON output for easy live verification**
- [ ] **Step 4: Re-run unit tests**
