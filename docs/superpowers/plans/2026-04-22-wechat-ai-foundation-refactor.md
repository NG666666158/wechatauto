# WeChat AI Foundation Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the target `wechat_ai` package layout and data directory structure without breaking the current WeChat 4.1+ auto-reply flows.

**Architecture:** Keep `pyweixin` unchanged as the UI automation layer and refactor only `wechat_ai` into bounded subpackages. Introduce new folders and compatibility imports first, then migrate runtime dependencies behind stable interfaces so the current entry scripts continue to work throughout the refactor.

**Tech Stack:** Python 3.14, file-backed JSON/Markdown data stores, existing `pyweixin` runtime, unittest-based regression scripts.

---

### Task 1: Create the Target Package Skeleton

**Files:**
- Create: `wechat_ai/orchestration/__init__.py`
- Create: `wechat_ai/profile/__init__.py`
- Create: `wechat_ai/rag/__init__.py`
- Create: `wechat_ai/memory/__init__.py`
- Create: `wechat_ai/data/.gitkeep`
- Create: `wechat_ai/data/users/.gitkeep`
- Create: `wechat_ai/data/agents/.gitkeep`
- Create: `wechat_ai/data/knowledge/.gitkeep`
- Create: `wechat_ai/data/memory/.gitkeep`
- Create: `wechat_ai/data/logs/.gitkeep`
- Modify: `README.md`

- [ ] Add the package and data directory skeleton with empty module exports only.
- [ ] Update `README.md` with one short section describing the new internal layout and clarifying that runtime scripts are unchanged.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Expected: all existing tests still pass.
- [ ] Commit: `git commit -m "chore: add wechat ai package skeleton"`

### Task 2: Add Shared Domain Models

**Files:**
- Create: `wechat_ai/models.py`
- Modify: `wechat_ai/__init__.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Define stable dataclasses for the internal runtime contract:

```python
from dataclasses import dataclass, field

@dataclass(slots=True)
class Message:
    chat_id: str
    chat_type: str
    sender_name: str
    text: str
    timestamp: str | None = None
    context: list[str] = field(default_factory=list)

@dataclass(slots=True)
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)
```

- [ ] Re-export these models from `wechat_ai/__init__.py` so future modules use one shared type source.
- [ ] Add focused tests that instantiate the dataclasses and verify default field behavior.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "refactor: add shared wechat ai models"`

### Task 3: Add Runtime Path Configuration Helpers

**Files:**
- Modify: `wechat_ai/config.py`
- Create: `wechat_ai/paths.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Introduce explicit path helpers for the new local data directories:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
USERS_DIR = DATA_DIR / "users"
AGENTS_DIR = DATA_DIR / "agents"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
MEMORY_DIR = DATA_DIR / "memory"
LOGS_DIR = DATA_DIR / "logs"
```

- [ ] Add a `bootstrap_data_dirs()` helper that creates missing directories during startup.
- [ ] Call the bootstrap helper from `WeChatAIApp.from_env()` before any profile or log access is introduced.
- [ ] Add tests that assert the helper resolves consistent paths without touching WeChat APIs.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "refactor: add wechat ai data path helpers"`

### Task 4: Prepare Compatibility Imports for Future Module Moves

**Files:**
- Modify: `wechat_ai/reply_engine.py`
- Modify: `wechat_ai/wechat_runtime.py`
- Create: `wechat_ai/orchestration/reply_pipeline.py`
- Test: `scripts/test_wechat_ai_unit.py`

- [ ] Create `wechat_ai/orchestration/reply_pipeline.py` with a thin placeholder pipeline object that simply delegates to the current reply engine.
- [ ] Update `wechat_ai/wechat_runtime.py` to depend on the compatibility layer instead of directly assuming prompt generation remains in one file.
- [ ] Keep existing public methods and return shapes unchanged.
- [ ] Add regression tests that prove `WeChatAIApp.from_env()` and `friend_callback()` still work through the compatibility layer.
- [ ] Run: `py -3 scripts\test_wechat_ai_unit.py`
- [ ] Commit: `git commit -m "refactor: add reply pipeline compatibility layer"`

### Task 5: Add a Refactor Safety Check Script

**Files:**
- Create: `scripts/test_wechat_ai_foundation_smoke.py`
- Modify: `README.md`

- [ ] Add a small smoke script that imports:
  - `wechat_ai.models`
  - `wechat_ai.paths`
  - `wechat_ai.reply_engine`
  - `wechat_ai.wechat_runtime`
- [ ] Print a JSON result with `ok: true` only when all imports succeed.
- [ ] Document the script in `README.md` under the AI runtime section.
- [ ] Run:

```powershell
py -3 scripts\test_wechat_ai_foundation_smoke.py
```

- [ ] Expected: JSON output with `"ok": true`
- [ ] Commit: `git commit -m "test: add wechat ai foundation smoke check"`
