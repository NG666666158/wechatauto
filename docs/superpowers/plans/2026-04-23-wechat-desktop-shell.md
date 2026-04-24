# 微信自动回复桌面应用壳 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为桌面前端补齐可对接的 Python 应用服务层，并实现拖拽文件导入本地知识库与重建索引的真实能力。

**Architecture:** 新增 `wechat_ai/app/` 作为桌面应用后端协议层，统一封装页面 DTO、设置存储、守护状态占位和知识库导入。真实能力优先落在首页状态、设置、知识库导入；消息和客户页先提供稳定接口与占位返回。

**Tech Stack:** Python 3、dataclasses、现有 `wechat_ai` runtime/profile/identity/memory/rag` 模块、文件型 JSON 存储、`unittest`

---

### Task 1: 扩展路径与应用层数据目录

**Files:**
- Modify: `wechat_ai/paths.py`
- Test: `scripts/test_wechat_ai_paths_unit.py`

- [ ] **Step 1: 写失败测试，约束应用层目录必须被创建**

```python
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from wechat_ai import paths


class PathsAppDirTests(TestCase):
    def test_bootstrap_creates_app_dirs(self) -> None:
        temp_root = Path(".tmp_wechat_ai_paths_app_dir")
        with patch.object(paths, "DATA_DIR", temp_root):
            with patch.object(paths, "APP_DIR", temp_root / "app"):
                with patch.object(paths, "APP_UPLOADS_DIR", temp_root / "app" / "uploads"):
                    created = paths.bootstrap_data_dirs()
                    self.assertIn(temp_root / "app", created)
                    self.assertTrue((temp_root / "app").exists())
                    self.assertTrue((temp_root / "app" / "uploads").exists())
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `py -3 scripts\test_wechat_ai_paths_unit.py`
Expected: FAIL，提示 `APP_DIR` 或 `APP_UPLOADS_DIR` 未定义，或 `bootstrap_data_dirs()` 未创建新目录。

- [ ] **Step 3: 在 `paths.py` 中补应用层目录**

```python
APP_DIR = DATA_DIR / "app"
APP_UPLOADS_DIR = KNOWLEDGE_DIR / "uploads"


def local_data_dirs() -> tuple[Path, ...]:
    return (
        DATA_DIR,
        USERS_DIR,
        AGENTS_DIR,
        KNOWLEDGE_DIR,
        APP_UPLOADS_DIR,
        APP_DIR,
        MEMORY_DIR,
        LOGS_DIR,
    )
```

- [ ] **Step 4: 重新运行路径测试**

Run: `py -3 scripts\test_wechat_ai_paths_unit.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add wechat_ai/paths.py scripts/test_wechat_ai_paths_unit.py
git commit -m "feat: add desktop app data directories"
```

### Task 2: 新增桌面应用数据模型与设置存储

**Files:**
- Create: `wechat_ai/app/models.py`
- Create: `wechat_ai/app/settings_store.py`
- Create: `wechat_ai/app/__init__.py`
- Test: `scripts/test_wechat_ai_app_service_unit.py`

- [ ] **Step 1: 写失败测试，约束设置默认值和 patch 更新**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wechat_ai.app.settings_store import DesktopSettingsStore


class DesktopSettingsStoreTests(TestCase):
    def test_load_defaults_when_file_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = DesktopSettingsStore(Path(temp_dir) / "desktop_settings.json")
            snapshot = store.load()
            self.assertTrue(snapshot.auto_reply_enabled)
            self.assertEqual(snapshot.work_hours.start, "09:00")
            self.assertEqual(snapshot.work_hours.end, "18:00")

    def test_update_persists_patch(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = DesktopSettingsStore(Path(temp_dir) / "desktop_settings.json")
            updated = store.update({"auto_reply_enabled": False, "reply_style": "专业友好"})
            self.assertFalse(updated.auto_reply_enabled)
            self.assertEqual(updated.reply_style, "专业友好")
            self.assertFalse(store.load().auto_reply_enabled)
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `py -3 scripts\test_wechat_ai_app_service_unit.py`
Expected: FAIL，提示 `wechat_ai.app` 或 `DesktopSettingsStore` 不存在。

- [ ] **Step 3: 实现桌面应用 DTO 与设置存储**

```python
@dataclass(slots=True)
class WorkHours:
    enabled: bool = True
    start: str = "09:00"
    end: str = "18:00"


@dataclass(slots=True)
class SettingsSnapshot:
    auto_reply_enabled: bool = True
    reply_style: str = "自然友好"
    new_customer_auto_create: bool = True
    sensitive_message_review: bool = True
    work_hours: WorkHours = field(default_factory=WorkHours)
```

```python
class DesktopSettingsStore:
    def load(self) -> SettingsSnapshot: ...
    def update(self, patch: Mapping[str, object]) -> SettingsSnapshot: ...
```

- [ ] **Step 4: 重新运行新测试**

Run: `py -3 scripts\test_wechat_ai_app_service_unit.py`
Expected: PASS，且不影响已有 profile/config 测试。

- [ ] **Step 5: Commit**

```bash
git add wechat_ai/app/models.py wechat_ai/app/settings_store.py wechat_ai/app/__init__.py scripts/test_wechat_ai_app_service_unit.py
git commit -m "feat: add desktop app settings store"
```

### Task 3: 新增知识库拖拽导入模块

**Files:**
- Create: `wechat_ai/app/knowledge_importer.py`
- Modify: `wechat_ai/rag/ingest.py`
- Test: `scripts/test_wechat_ai_knowledge_importer_unit.py`

- [ ] **Step 1: 写失败测试，约束拖拽文件导入与索引状态**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wechat_ai.app.knowledge_importer import KnowledgeImporter


class KnowledgeImporterTests(TestCase):
    def test_import_txt_file_copies_and_rebuilds_index(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "faq.txt"
            source.write_text("退款说明：支持 7 天内申请。", encoding="utf-8")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            result = importer.import_files([source])
            self.assertEqual(result.files[0].status, "imported")
            self.assertTrue((root / "knowledge" / "uploads" / "faq.txt").exists())
            self.assertTrue((root / "knowledge" / "local_knowledge_index.json").exists())

    def test_import_unsupported_file_reports_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "diagram.png"
            source.write_bytes(b"fake")
            importer = KnowledgeImporter(
                knowledge_dir=root / "knowledge",
                uploads_dir=root / "knowledge" / "uploads",
                index_path=root / "knowledge" / "local_knowledge_index.json",
            )
            result = importer.import_files([source], rebuild_index=False)
            self.assertEqual(result.files[0].status, "unsupported")
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `py -3 scripts\test_wechat_ai_knowledge_importer_unit.py`
Expected: FAIL，提示 `KnowledgeImporter` 不存在。

- [ ] **Step 3: 实现导入器和可扩展提取器**

```python
class KnowledgeImporter:
    def import_files(self, file_paths: Sequence[Path], rebuild_index: bool = True) -> KnowledgeImportResult: ...
    def rebuild_index(self) -> KnowledgeIndexStatus: ...
    def list_files(self) -> list[KnowledgeFileRecord]: ...
    def get_status(self) -> KnowledgeIndexStatus: ...
```

```python
def load_knowledge_documents(root_dir: Path | None = None) -> list[KnowledgeDocument]:
    ...
```

要求：
- 继续支持现有 `.txt` / `.md` / `.json`
- 提取器注册表预留 `.pdf` / `.docx`
- 导入失败返回逐文件原因

- [ ] **Step 4: 重新运行知识库测试**

Run: `py -3 scripts\test_wechat_ai_knowledge_importer_unit.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add wechat_ai/app/knowledge_importer.py wechat_ai/rag/ingest.py scripts/test_wechat_ai_knowledge_importer_unit.py
git commit -m "feat: add drag-and-drop knowledge importer"
```

### Task 4: 新增桌面应用服务层

**Files:**
- Create: `wechat_ai/app/service.py`
- Test: `scripts/test_wechat_ai_app_service_unit.py`

- [ ] **Step 1: 写失败测试，约束首页/设置/知识库接口**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wechat_ai.app.service import DesktopAppService


class DesktopAppServiceTests(TestCase):
    def test_get_app_status_returns_dashboard_shape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service = DesktopAppService(data_root=Path(temp_dir))
            status = service.get_app_status()
            self.assertIn(status.wechat_status, {"unknown", "connected", "disconnected"})
            self.assertIn(status.daemon_state, {"stopped", "running", "paused"})

    def test_settings_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service = DesktopAppService(data_root=Path(temp_dir))
            updated = service.update_settings({"reply_style": "专业友好"})
            self.assertEqual(updated.reply_style, "专业友好")

    def test_message_placeholders_are_structured(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service = DesktopAppService(data_root=Path(temp_dir))
            result = service.send_reply("friend:alice", "你好")
            self.assertEqual(result["status"], "not_implemented")
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `py -3 scripts\test_wechat_ai_app_service_unit.py`
Expected: FAIL，提示 `DesktopAppService` 不存在。

- [ ] **Step 3: 实现服务层**

```python
class DesktopAppService:
    def get_app_status(self) -> AppStatus: ...
    def get_settings(self) -> SettingsSnapshot: ...
    def update_settings(self, patch: Mapping[str, object]) -> SettingsSnapshot: ...
    def import_knowledge_files(self, paths: Sequence[Path]) -> KnowledgeImportResult: ...
    def get_knowledge_status(self) -> KnowledgeIndexStatus: ...
    def list_conversations(self) -> list[ConversationListItem]: ...
    def send_reply(self, conversation_id: str, text: str) -> dict[str, str]: ...
```

实现要求：
- 首页状态真实读取设置和索引状态
- 守护启停先操作应用层状态文件
- 消息/客户接口显式占位

- [ ] **Step 4: 重新运行应用服务测试**

Run: `py -3 scripts\test_wechat_ai_app_service_unit.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add wechat_ai/app/service.py scripts/test_wechat_ai_app_service_unit.py
git commit -m "feat: add desktop app service facade"
```

### Task 5: 集成回归与文档补充

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture-overview.md`
- Optional: `PROJECT_PLAN.md`

- [ ] **Step 1: 补充桌面应用后端接口和知识库拖拽说明**

```markdown
## 桌面应用后端接口层

当前仓库已新增 `wechat_ai/app/`，用于给后续桌面前端提供稳定接口。

## 本地知识库拖拽导入

可通过 `DesktopAppService.import_knowledge_files(...)` 或后续前端拖拽入口导入文件并重建索引。
```

- [ ] **Step 2: 运行本轮最小回归集**

Run:
`py -3 scripts\test_wechat_ai_paths_unit.py`
`py -3 scripts\test_wechat_ai_app_service_unit.py`
`py -3 scripts\test_wechat_ai_knowledge_importer_unit.py`
`py -3 scripts\test_wechat_ai_reply_pipeline_unit.py`
`py -3 scripts\test_wechat_ai_identity_integration_unit.py`

Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add README.md docs/architecture-overview.md PROJECT_PLAN.md
git commit -m "docs: document desktop app backend shell"
```
