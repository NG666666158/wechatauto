# P8 Productization Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the desktop app into a "usable operations console" by validating the identity prompt pipeline, knowledge-base pipeline, and long-run WeChat automation stability before broader release.

**Architecture:** P8 does not add a new runtime. It hardens and verifies the existing stack: Electron desktop shell for configuration and visibility, FastAPI local API for state and control, and the current WeChat runtime for reply execution. The desktop client remains the place to edit identity/self-identity, knowledge, schedule, and metrics; the actual message execution loop stays in the Python runtime.

**Tech Stack:** Electron, Next.js App Router, FastAPI, local JSON/JSONL stores, existing prompt pipeline, local knowledge importer/retriever, Windows UI automation scripts.

---

## Scope

P8 is explicitly about release gating, not broad new feature expansion. The acceptance focus is:

1. **Identity prompt chain is inspectable and correct**
   - User identity / self-identity can be edited from the desktop client.
   - Those settings are actually visible in prompt-preview or runtime prompt evidence.
2. **Knowledge pipeline is inspectable and correct**
   - Local import, web-build, and retrieval work through desktop client and API.
   - Retrieved chunks can be observed and correlated to reply generation.
3. **WeChat runtime is stable enough for long-run use**
   - The app survives focus changes, window state changes, network/model failures, and restart flows.
   - No duplicate sending, no infinite log growth, no unrecoverable stop state.
4. **Desktop shell is operationally usable**
   - Settings are visible and editable.
   - Schedule / launch-at-login / silent-run preferences behave predictably.
   - The app opens reliably and diagnostics are available when it does not.

## File Map

**Likely to modify**
- `desktop_app/frontend/app/settings/page.tsx`
- `desktop_app/frontend/app/customers/page.tsx`
- `desktop_app/frontend/app/knowledge/page.tsx`
- `desktop_app/frontend/app/messages/page.tsx`
- `desktop_app/frontend/lib/api.ts`
- `desktop_app/frontend/lib/electron-shell.ts`
- `desktop_app/frontend/tests/p5-frontend-acceptance.mjs`
- `desktop_app/electron/main.cjs`
- `desktop_app/electron/window-diagnostics.cjs`
- `desktop_app/electron/window-visibility-controller.cjs`
- `desktop_app/electron/tests/p7-shell-unit.mjs`
- `wechat_ai/orchestration/reply_pipeline.py`
- `wechat_ai/orchestration/prompt_builder.py`
- `wechat_ai/app/service.py`
- `wechat_ai/server/api/identity.py`
- `wechat_ai/server/api/knowledge.py`
- `wechat_ai/server/api/logs.py`
- `wechat_ai/wechat_runtime.py`
- `scripts/long_run_observer.py`
- `scripts/probe_wechat_window.py`
- `scripts/test_wechat_ai_server_unit.py`
- `scripts/test_wechat_ai_unit.py`
- `scripts/test_wechat_ai_app_service_unit.py`
- `REFACTOR_PLAN.md`

**Likely to create**
- `desktop_app/frontend/app/observability/page.tsx` or a light diagnostics panel inside an existing page
- `wechat_ai/server/api/debug.py` or equivalent prompt-preview/read-only inspection endpoint
- `scripts/run_p8_acceptance.py`
- `docs/p8-acceptance-checklist.md`
- `docs/p8-runbook.md`
- `docs/p8-long-run-report-template.md`

---

### Task 1: Freeze P8 Acceptance Surface

**Files:**
- Modify: `REFACTOR_PLAN.md`
- Create: `docs/p8-acceptance-checklist.md`
- Create: `docs/p8-runbook.md`

- [ ] **Step 1: Write the failing documentation expectation**

Define the exact P8 release gate in `docs/p8-acceptance-checklist.md`:

```md
## P8 Acceptance Gate

- Identity edits can be made from the client and reflected in prompt evidence.
- Knowledge import/search/web-build can be triggered from the client and verified by evidence.
- Electron shell can open settings reliably and expose shell preferences.
- 30m / 2h / 8h reports all produce structured output.
- No duplicate sends, no stuck stop state, no uncontrolled log growth.
```

- [ ] **Step 2: Update the refactor plan so P8 scope is explicit**

Add or rewrite the `P8` section in `REFACTOR_PLAN.md` so it no longer reads as only "long-run observer", but as:

```md
- P8-1 Identity prompt chain acceptance
- P8-2 Knowledge retrieval chain acceptance
- P8-3 Desktop-shell operational acceptance
- P8-4 30m / 2h / 8h long-run stability
- P8-5 Release checklist and runbook
```

- [ ] **Step 3: Write the operator runbook skeleton**

In `docs/p8-runbook.md`, add:

```md
1. Start frontend
2. Start Electron
3. Confirm backend health
4. Confirm identity page / knowledge page / settings page
5. Run 30m smoke
6. Capture artifacts
7. Resume or stop runtime cleanly
```

- [ ] **Step 4: Review docs for overlap**

Check `docs/desktop-app-backend.md` and `REFACTOR_PLAN.md` for duplicated or contradictory acceptance wording and normalize them.

- [ ] **Step 5: Verification**

Run:

```powershell
py -3 -c "from pathlib import Path; print(Path('docs/p8-acceptance-checklist.md').exists(), Path('docs/p8-runbook.md').exists())"
```

Expected: `True True`

---

### Task 2: Identity Prompt Chain Acceptance

**Files:**
- Modify: `desktop_app/frontend/app/customers/page.tsx`
- Modify: `wechat_ai/orchestration/reply_pipeline.py`
- Modify: `wechat_ai/orchestration/prompt_builder.py`
- Modify: `wechat_ai/server/api/identity.py`
- Modify: `scripts/test_wechat_ai_unit.py`
- Create: `docs/api-contract/fixtures/customers/identity.prompt-preview.json`

- [ ] **Step 1: Add a read-only identity prompt evidence path**

Add a safe inspection surface that returns prompt-related evidence without sending a message:

```json
{
  "resolved_user_id": "user_001",
  "self_identity_profile": {
    "display_name": "碱水",
    "identity_facts": ["我是产品顾问"]
  },
  "identity_status": "confirmed",
  "identity_confidence": 0.92
}
```

- [ ] **Step 2: Ensure customer-side identity edits are tied to actual prompt input**

Verify the desktop client path is not "UI-only". The evidence endpoint or prompt-preview output must be built from the same resolver chain the runtime uses.

- [ ] **Step 3: Add a failing unit test**

Add a test in `scripts/test_wechat_ai_unit.py` or the closest prompt-pipeline test module asserting:

```python
assert "我是产品顾问" in preview["self_identity_profile"]["identity_facts"]
assert preview["resolved_user_id"] == "user_001"
```

- [ ] **Step 4: Make the test pass with minimal changes**

Only surface already-existing resolution results; do not build a second identity pipeline.

- [ ] **Step 5: Verification**

Run:

```powershell
py -3 scripts\test_wechat_ai_unit.py
py -3 scripts\test_wechat_ai_server_unit.py
```

Expected: both pass

---

### Task 3: Knowledge Pipeline Acceptance

**Files:**
- Modify: `desktop_app/frontend/app/knowledge/page.tsx`
- Modify: `wechat_ai/app/service.py`
- Modify: `wechat_ai/server/api/knowledge.py`
- Modify: `scripts/test_wechat_ai_app_service_unit.py`
- Modify: `scripts/test_wechat_ai_server_unit.py`
- Create: `docs/api-contract/fixtures/knowledge/knowledge.acceptance.json`

- [ ] **Step 1: Define the knowledge acceptance artifact**

Record one successful import/search/web-build evidence shape:

```json
{
  "imported_files": ["product.pdf"],
  "search_query": "试用政策",
  "retrieved_chunk_ids": ["chunk_001"],
  "web_build_status": "built"
}
```

- [ ] **Step 2: Add a failing service/unit test**

Assert the service can:

```python
status = service.get_knowledge_status()
assert "supported_extensions" in status
result = service.search_knowledge("试用政策", limit=3)
assert isinstance(result, list)
```

- [ ] **Step 3: Add a UI acceptance check**

Update `desktop_app/frontend/tests/p5-frontend-acceptance.mjs` (or add a P8 acceptance script) to verify the knowledge page still exposes:

```js
source.includes("importKnowledgeFiles")
source.includes("buildWebKnowledgeFromDocuments")
source.includes("searchKnowledge")
```

- [ ] **Step 4: Verification**

Run:

```powershell
py -3 scripts\test_wechat_ai_app_service_unit.py
py -3 scripts\test_wechat_ai_server_unit.py
node desktop_app\frontend\tests\p5-frontend-acceptance.mjs
```

Expected: all pass

---

### Task 4: Desktop Shell Operational Acceptance

**Files:**
- Modify: `desktop_app/electron/main.cjs`
- Modify: `desktop_app/electron/window-diagnostics.cjs`
- Modify: `desktop_app/electron/tests/p7-shell-unit.mjs`
- Modify: `desktop_app/frontend/app/settings/page.tsx`
- Create: `scripts/run_p8_acceptance.py`

- [ ] **Step 1: Formalize shell diagnostics output**

Make the shell emit stable events/log lines for:

```text
[electron-shell] window.did_start_loading
[electron-shell] window.dom_ready
[electron-shell] window.did_finish_load
[electron-shell] window.did_fail_load
```

- [ ] **Step 2: Confirm settings-page desktop preferences are visible**

The acceptance script should verify the settings page contains:

```text
开机自启
定时巡检间隔
```

This can be DOM inspection, page text inspection, or a route-level content probe.

- [ ] **Step 3: Add a failing shell unit/integration check**

Extend `p7-shell-unit.mjs` or `run_p8_acceptance.py` to fail when:

```text
- the Electron window never reaches dom-ready/did-finish-load
- the settings route cannot be loaded
- desktop shell preferences bridge is unavailable in Electron mode
```

- [ ] **Step 4: Verification**

Run:

```powershell
node desktop_app\electron\tests\p7-shell-unit.mjs
node desktop_app\electron\tests\p7-shell-preferences-bridge-unit.mjs
desktop_app\frontend: npx tsc --noEmit --pretty false
```

Expected: all pass

---

### Task 5: Long-Run Stability Gate

**Files:**
- Modify: `scripts/long_run_observer.py`
- Modify: `scripts/probe_wechat_window.py`
- Create: `docs/p8-long-run-report-template.md`
- Create: `scripts/run_p8_acceptance.py`

- [ ] **Step 1: Freeze the three run durations**

Add stable entrypoints or flags for:

```text
30 minutes smoke
120 minutes stability
480 minutes long run
```

- [ ] **Step 2: Freeze artifact format**

Every run should output:

```json
{
  "duration_minutes": 30,
  "errors": 0,
  "duplicate_send_count": 0,
  "window_state_changes": [],
  "model_failures": [],
  "network_failures": [],
  "send_confirm_failures": [],
  "memory_growth": {},
  "log_growth": {}
}
```

- [ ] **Step 3: Cover required disturbance scenarios**

At minimum the acceptance checklist must include:

```text
- WeChat closed
- WeChat minimized
- network interruption
- model failure / timeout
- send confirmation failure
```

- [ ] **Step 4: Verification**

Run:

```powershell
py -3 scripts\long_run_observer.py --target-duration-minutes 30 --format json
```

Expected: a structured JSON report is produced

---

### Task 6: Final Release Gate and Handoff

**Files:**
- Modify: `REFACTOR_PLAN.md`
- Modify: `README.md`
- Create: `docs/p8-release-checklist.md`

- [ ] **Step 1: Define release criteria**

Write the exact gate:

```md
- Identity prompt evidence verified
- Knowledge retrieval evidence verified
- Desktop preferences visible and editable in Electron
- 30m smoke passed
- 2h stability passed
- 8h long-run passed
```

- [ ] **Step 2: Update README positioning**

Clarify in `README.md`:

```md
Desktop app role: configuration, identity editing, knowledge management, observability, and scheduling.
Runtime role: actual WeChat reply execution, which still occupies foreground input during operation.
```

- [ ] **Step 3: Verification**

Run:

```powershell
py -3 scripts\test_wechat_ai_server_unit.py
py -3 scripts\test_wechat_ai_api_contract_unit.py
py -3 scripts\test_wechat_ai_app_service_unit.py
py -3 scripts\test_wechat_ai_unit.py
node desktop_app\electron\tests\p7-shell-unit.mjs
node desktop_app\frontend\tests\p5-frontend-acceptance.mjs
desktop_app\frontend: npx tsc --noEmit --pretty false
```

Expected: all pass before P8 can be marked complete

---

## Self-Review

**Spec coverage:** The plan covers the three product-critical chains the user described: identity facts feeding prompt construction, knowledge-base construction/retrieval feeding answers, and desktop client positioning as configuration/monitoring shell rather than background no-input automation.

**Placeholder scan:** No `TODO`/`TBD` placeholders were left. The acceptance artifacts, files, and verification commands are explicit.

**Type consistency:** The plan keeps the current architecture boundaries intact: Electron shell preferences stay in the shell, runtime settings stay in `/api/v1/settings`, and prompt/knowledge evidence comes from the existing Python pipeline rather than a second mock path.
