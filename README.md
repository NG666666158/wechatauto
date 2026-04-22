# pywechat

这是一个基于 Windows 微信桌面端自动化能力构建的项目，并在其上增加了本地 `wechat_ai` 运行时，用于实现 AI 自动回复、画像感知提示词组装、本地知识检索、结构化可观测性以及轻量记忆能力。

## 项目定位

当前仓库可以理解为两层结构：

1. `pywechat` / `pyweixin`
   原始的 Windows 微信桌面自动化能力，负责打开窗口、读取消息、发送回复等 UI 自动化动作。
2. `wechat_ai`
   新增的 AI 运行时层，负责组织消息上下文、画像、知识、记忆、模型调用与调试日志。

如果你是第一次阅读这个项目，建议按照下面顺序看文档：

1. 当前这份 `README.md`
2. [架构总览](/C:/github/pywechat/pywechat-main/pywechat-main/docs/architecture-overview.md)
3. [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)

## 当前已具备的能力

- 基于 MiniMax 的好友自动回复
- 微信群聊 `@` 场景自动回复
- 全局轮询未读会话，并兼顾当前激活聊天窗口
- 结构化提示词组装，支持：
  - 最近消息上下文
  - 用户画像摘要
  - 助手画像摘要
  - 本地知识检索结果
  - 可选的记忆摘要
- 本地 RAG 基础能力：知识导入、分块、嵌入抽象、检索
- 结构化 JSONL 运行时日志
- 按 `chat_id` 存储的轻量记忆文件
- 最近日志与记忆摘要查看脚本
- 覆盖 `wechat_ai` 运行时主要模块的单测与 smoke 验证

## 仓库结构

最常用的目录和文件如下：

- `pywechat/`
  旧有桌面自动化模块
- `pyweixin/`
  兼容当前微信流程的桌面自动化模块
- `wechat_ai/`
  新的 AI 运行时
- `scripts/`
  运行入口、知识导入、调试脚本与测试脚本
- `docs/architecture-overview.md`
  当前主架构说明文档
- `PROJECT_PLAN.md`
  当前阶段状态、路线图和长期使用前的收尾清单
- `docs/superpowers/`
  历史设计稿、阶段计划和实现记录，不再作为项目主入口文档

## 快速开始

### 1. 安装依赖

```powershell
py -3 -m pip install -r requirements.txt
```

### 2. 配置运行环境

最少需要设置：

- `MINIMAX_API_KEY`

可选环境变量包括：

- `MINIMAX_MODEL`
- `WECHAT_CONTEXT_LIMIT`
- `WECHAT_GROUP_MENTION_NAMES`

如果不额外覆盖，画像、知识、日志、记忆等运行时数据都会默认落在 `wechat_ai/data/` 下。

### 3. 运行一个自动回复模式

单好友自动回复：

```powershell
py -3 scripts\run_minimax_friend_auto_reply.py --friend "Alice" --duration 5min --debug
```

群聊 `@` 自动回复：

```powershell
py -3 scripts\run_minimax_group_at_reply.py --group "Project Group" --duration 5min --debug
```

全局轮询模式：

```powershell
py -3 scripts\run_minimax_global_auto_reply.py --duration 5min --poll-interval 1.0 --debug
```

## 知识库与提示词调试

构建或重建本地知识索引：

```powershell
py -3 scripts\ingest_knowledge.py
py -3 scripts\rebuild_index.py
```

在不打开微信的情况下预览提示词：

```powershell
py -3 scripts\test_prompt_preview.py
```

## 可观测性与记忆

运行时当前会写出两类本地数据：

- 结构化事件日志：`wechat_ai/data/logs/runtime_events.jsonl`
- 轻量记忆文件：`wechat_ai/data/memory/`

当你在运行脚本时加上 `--debug`，建议排障第一步先看这两个入口：

```powershell
py -3 scripts\show_recent_logs.py --limit 20
py -3 scripts\show_memory_summary.py --chat-id friend_demo
```

当前日志事件包括：

- `message_received`
- `profile_loaded`
- `retrieval_completed`
- `prompt_built`
- `model_completed`
- `fallback_used`
- `message_sent`

提示词预览会在写日志前做截断，fallback 日志只记录异常类型和异常信息，不记录 API Key 等敏感内容。

## 测试

当前 `wechat_ai` 运行时的核心回归命令：

```powershell
py -3 scripts\test_wechat_ai_unit.py
py -3 scripts\test_wechat_ai_models_unit.py
py -3 scripts\test_wechat_ai_orchestration_context_unit.py
py -3 scripts\test_wechat_ai_pipeline_unit.py
py -3 scripts\test_wechat_ai_prompt_builder_unit.py
py -3 scripts\test_wechat_ai_reply_pipeline_unit.py
py -3 scripts\test_wechat_ai_profile_models_unit.py
py -3 scripts\test_wechat_ai_profile_config_unit.py
py -3 scripts\test_wechat_ai_profile_store_unit.py
py -3 scripts\test_wechat_ai_paths_unit.py
py -3 scripts\test_wechat_ai_rag_chunking_unit.py
py -3 scripts\test_wechat_ai_rag_loading_unit.py
py -3 scripts\test_wechat_ai_rag_retrieval_unit.py
py -3 scripts\test_wechat_ai_observability_scripts_unit.py
py -3 scripts\test_wechat_ai_foundation_smoke.py
py -3 scripts\test_prompt_preview.py
```

仍然保留的旧有 smoke/回归脚本：

- `scripts/test_pyweixin_smoke.py`
- `scripts/test_pull_messages_regression.py`
- `scripts/start_pyweixin.py`

## 文档导航

如果你想理解“现在这个项目到底是什么”，建议按以下顺序阅读：

1. [README.md](/C:/github/pywechat/pywechat-main/pywechat-main/README.md)
2. [架构总览](/C:/github/pywechat/pywechat-main/pywechat-main/docs/architecture-overview.md)
3. [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)

历史演进记录：

- [全局设计规格](/C:/github/pywechat/pywechat-main/pywechat-main/docs/superpowers/specs/2026-04-22-global-wechat-ai-design.md)
- [阶段计划目录](/C:/github/pywechat/pywechat-main/pywechat-main/docs/superpowers/plans)

## 历史资料

仓库里仍然保留了原始桌面自动化层的资料：

- [Weixin4.0.md](/C:/github/pywechat/pywechat-main/pywechat-main/Weixin4.0.md)
- `pywechat操作手册.docx`
- `pyweixin操作手册.docx`
- `pywinauto使用方法.ipynb`

这些资料对理解底层微信自动化细节仍然有帮助，但已经不适合作为理解当前 `wechat_ai` 运行时的第一入口。
