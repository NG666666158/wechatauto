# 分层自我身份系统设计

目标是在现有用户身份识别、用户画像、记忆与回复编排之上，增加一套“我是谁”的分层事实系统，使回复时能同时考虑全局自我身份、关系型自我身份和对象级自我身份覆盖。

## 设计目标

- 全局保存一份稳定的自我事实身份，不再把所有“我是谁”都塞进单一 `AgentProfile`
- 支持面对不同关系对象时叠加不同的事实身份模板，例如老师、父母、客户、朋友
- 支持针对具体对象做少量高优先级覆盖，例如“对张老师我是 2023 级某班学生”
- 回复阶段按统一优先级合并，避免桌面端、CLI、回复提示词各写一套逻辑
- 保持和现有 `identity/profile/reply_pipeline/app service` 结构兼容，尽量少侵入

## 分层模型

### 1. 全局自我身份

保存所有关系都成立的稳定事实，例如：

- 姓名、职业、学校、城市
- 家庭或工作中的稳定角色
- 长期不变的背景事实
- 禁止编造或容易冲突的身份边界

### 2. 关系型自我身份模板

按关系标签维护模板，例如：

- `teacher`
- `parent`
- `friend`
- `customer`
- `colleague`

每个模板包含：

- 面对该关系时我的事实身份
- 推荐语气和表达约束
- 互动注意事项
- 命中的关系标签说明

### 3. 对象级自我身份覆盖

按 `resolved_user_id` 保存具体对象的覆盖项，只保存少量高优先级补充，例如：

- 对张老师：我是 2023 级 XX 班学生
- 对妈妈：我最近在做这个项目，作息偏晚
- 对某客户：我负责售后答疑，不负责报价审批

## 优先级规则

统一按以下顺序合并：

1. 对象级覆盖
2. 关系型模板
3. 全局自我身份

合并结果产出一个 `ResolvedSelfIdentityProfile`，供回复链路消费。

## 关系来源

关系标签优先从现有数据推导：

- `UserProfile.tags`
- `Message.relationship_to_me`
- 桌面端或 CLI 手动设置的 per-user relationship override

如果多个来源冲突，优先级为：

1. 对象级 relationship override
2. 用户画像中的人工标签
3. 自动识别结果

## 代码结构

- `wechat_ai/self_identity/models.py`
  定义全局身份、关系模板、对象覆盖、合并结果模型
- `wechat_ai/self_identity/store.py`
  负责 JSON 持久化、列表、读取、更新
- `wechat_ai/self_identity/resolver.py`
  根据用户画像、identity 结果和 override 合并出生效身份
- `wechat_ai/self_identity/admin.py`
  提供 CLI 与桌面端 service 复用接口
- `wechat_ai/app/service.py`
  增加桌面后端接口：读取和更新全局身份、关系模板、对象覆盖、预览生效身份
- `wechat_ai/orchestration/reply_pipeline.py`
  接入 `self_identity_resolver`，把合并结果注入 prompt preview 与回复构建
- `wechat_ai/orchestration/prompt_builder.py`
  增加“自我身份摘要”片段，避免只依赖 `AgentProfile`

## 数据目录

新增：

- `wechat_ai/data/self_identity/global_profile.json`
- `wechat_ai/data/self_identity/relationship_profiles/<relationship>.json`
- `wechat_ai/data/self_identity/user_overrides/<resolved_user_id>.json`

## 回复链路

1. `wechat_runtime` 继续产出 `Message` 的 identity metadata
2. `ReplyPipeline` 加载：
   - agent profile
   - user profile
   - resolved self identity profile
   - memory
   - knowledge
3. `PromptBuilder` 将 `self identity summary` 纳入提示词
4. 回复时优先遵守事实身份与关系语境，风格仍由 agent/profile 协同控制

## 风险与约束

- 不把关系自动识别做成强制结论，始终允许人工修正
- 自我身份只保存事实与沟通约束，不直接存大段生成式 prompt
- 对象级覆盖只做最小补充，避免长期膨胀
- 默认兼容旧链路：未配置自我身份时，回复链路照常工作

## 验证重点

- store 的读写、默认值和安全文件名
- 关系优先级合并规则
- `ReplyPipeline` 能加载并注入自我身份摘要
- 桌面端 `service` 能返回全局身份、关系模板、对象覆盖和预览结果
- 未配置自我身份时兼容旧链路
