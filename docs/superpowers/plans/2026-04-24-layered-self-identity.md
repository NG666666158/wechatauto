# 分层自我身份系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为微信自动回复后端增加全局/关系/对象三级自我身份系统，并接入回复链路与桌面端后端接口。

**Architecture:** 新增独立 `self_identity` 模块承载数据模型、store、resolver、admin；`ReplyPipeline` 只消费合并后的结果；`app/service` 暴露桌面端所需读写与预览接口。保持和现有 `profile/identity` 兼容，未配置时自动回退。

**Tech Stack:** Python dataclasses、JSON file storage、现有 `wechat_ai` profile/identity/reply pipeline/app service 架构、unittest 脚本。

---

### Task 1: 自我身份数据模型与存储

**Files:**
- Create: `wechat_ai/self_identity/models.py`
- Create: `wechat_ai/self_identity/store.py`
- Create: `wechat_ai/self_identity/__init__.py`
- Test: `scripts/test_wechat_ai_self_identity_store_unit.py`

- [ ] 写失败测试，覆盖全局身份、关系模板、对象覆盖的 round-trip 与默认值
- [ ] 运行 `py -3 scripts/test_wechat_ai_self_identity_store_unit.py`，确认失败
- [ ] 实现 dataclass 模型与 JSON store
- [ ] 再次运行 `py -3 scripts/test_wechat_ai_self_identity_store_unit.py`，确认通过

### Task 2: 合并解析器与优先级规则

**Files:**
- Create: `wechat_ai/self_identity/resolver.py`
- Test: `scripts/test_wechat_ai_self_identity_resolver_unit.py`

- [ ] 写失败测试，覆盖“对象级 > 关系级 > 全局级”的合并规则
- [ ] 增加关系来源测试：`UserProfile.tags`、`relationship_to_me`、manual override
- [ ] 实现 resolver、关系解析和摘要生成
- [ ] 运行 `py -3 scripts/test_wechat_ai_self_identity_resolver_unit.py`，确认通过

### Task 3: ReplyPipeline 接入自我身份

**Files:**
- Modify: `wechat_ai/orchestration/reply_pipeline.py`
- Modify: `wechat_ai/orchestration/prompt_builder.py`
- Test: `scripts/test_wechat_ai_reply_pipeline_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_integration_unit.py`

- [ ] 先写失败测试，确认 pipeline 会加载并合并 self identity
- [ ] 实现 pipeline 注入和 prompt preview 片段
- [ ] 验证未配置自我身份时仍兼容旧链路
- [ ] 运行相关测试并确认通过

### Task 4: 桌面端后端接口与 admin

**Files:**
- Create: `wechat_ai/self_identity/admin.py`
- Modify: `wechat_ai/app/service.py`
- Test: `scripts/test_wechat_ai_app_service_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_admin_unit.py`

- [ ] 为全局身份、关系模板、对象覆盖、预览结果写失败测试
- [ ] 实现 CLI 与桌面 service 的读写接口
- [ ] 确保桌面端可以预览某个用户当前生效的自我身份摘要
- [ ] 运行相关测试并确认通过

### Task 5: 全链路回归

**Files:**
- Modify: 仅在必要时修回归
- Test: `scripts/test_wechat_ai_unit.py`
- Test: `scripts/test_wechat_ai_reply_pipeline_unit.py`
- Test: `scripts/test_wechat_ai_app_service_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_store_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_resolver_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_integration_unit.py`
- Test: `scripts/test_wechat_ai_self_identity_admin_unit.py`

- [ ] 跑新旧测试，确认没有带出回归
- [ ] 修复回归问题
- [ ] 复跑并整理结果
