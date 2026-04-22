# 文档体系重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构仓库主文档体系，让 README、项目计划与架构文档分别面向不同读者并承担清晰职责。

**Architecture:** 将 `README.md` 提升为主入口文档，将 `PROJECT_PLAN.md` 收敛为路线图与完成度追踪文档，并在 `docs/` 下新增独立架构文档负责完整模块说明。`docs/superpowers/` 保留为历史设计和计划记录，但不再作为首要阅读路径。

**Tech Stack:** Markdown、仓库目录结构、当前 `wechat_ai` 运行时模块、现有脚本与测试。

---

### 任务 1：梳理当前文档职责

**Files:**
- Modify: `docs/superpowers/plans/2026-04-22-documentation-restructure.md`
- Read: `README.md`
- Read: `PROJECT_PLAN.md`
- Read: `docs/superpowers/specs/2026-04-22-global-wechat-ai-design.md`
- Read: `docs/superpowers/plans/*.md`

- [ ] 明确三份目标主文档，并为每份文档指定主要读者。
- [ ] 明确哪些内容应从 `README.md` 下沉到架构文档。
- [ ] 明确哪些内容应该只保留在 `PROJECT_PLAN.md` 作为路线图/状态说明。
- [ ] 明确 `docs/superpowers/` 只作为历史设计/计划记录，而不是当前主入口。

### 任务 2：将 README.md 改写为主入口文档

**Files:**
- Modify: `README.md`

- [ ] 增加清晰的项目摘要，说明仓库是“微信桌面自动化 + `wechat_ai` 运行时”两层结构。
- [ ] 增加以下章节：
  - 当前能力
  - 仓库结构
  - 快速开始
  - 关键运行脚本
  - 可观测性与记忆调试
  - 测试命令
  - 文档导航
- [ ] 从 README 中移除过深的设计解释和模块细节。
- [ ] 保留 `pywechat` / `pyweixin` 历史资料入口，但不再让它们占据主阅读路径。

### 任务 3：将 PROJECT_PLAN.md 重构为路线图与状态文档

**Files:**
- Modify: `PROJECT_PLAN.md`

- [ ] 用路线图导向的内容替换当前混合式架构/设计草稿。
- [ ] 增加以下章节：
  - 项目定位
  - 阶段交付总结
  - 当前完成状态
  - 已具备能力
  - 离长期使用还差什么
  - 最终收尾清单
- [ ] 移除会与 `docs/architecture-overview.md` 重复的模块细节说明。

### 任务 4：新增独立的架构总览文档

**Files:**
- Create: `docs/architecture-overview.md`

- [ ] 增加高层架构说明，解释 `pywechat` / `pyweixin` 自动化层与 `wechat_ai` 运行时如何配合。
- [ ] 说明以下关键模块：
  - `wechat_ai/wechat_runtime.py`
  - `wechat_ai/reply_engine.py`
  - `wechat_ai/orchestration/`
  - `wechat_ai/profile/`
  - `wechat_ai/rag/`
  - `wechat_ai/memory/`
  - `wechat_ai/logging_utils.py`
  - `wechat_ai/data/`
  - `scripts/`
- [ ] 说明从消息进入到回复生成、发送、日志记录、记忆写回的运行时数据流。
- [ ] 说明画像、知识、日志、记忆的本地存储布局。
- [ ] 说明调试流程与测试版图。

### 任务 5：互链与一致性复查

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_PLAN.md`
- Modify: `docs/architecture-overview.md`

- [ ] 确保三份主文档之间互相链接，并且有明确的“从哪里开始 / 想深入去哪里看”说明。
- [ ] 确保 README 和架构文档对“历史设计文档”的表述一致。
- [ ] 确保 `PROJECT_PLAN.md` 中的长期使用前清单符合当前仓库真实状态。
- [ ] 联读三份主文档，移除不再适合重复保留的说明。
