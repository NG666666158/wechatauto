# 架构总览

## 文档目的

这份文档用于说明当前仓库的整体结构：它既是一个 Windows 微信桌面自动化项目，也是在自动化层之上叠加了一套增强版 `wechat_ai` 运行时。

建议先读 [README.md](/C:/github/pywechat/pywechat-main/pywechat-main/README.md)。如果你更关心项目还差什么、是否适合长期使用，请读 [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)。

历史设计稿和阶段计划保存在 [docs/superpowers/](/C:/github/pywechat/pywechat-main/pywechat-main/docs/superpowers) 下，那部分文档描述的是演进过程；本文件描述的是当前状态。

## 系统分层

现在这个仓库可以分成两大层：

1. 桌面自动化层
   主要由 `pywechat/` 和 `pyweixin/` 提供，负责打开微信窗口、识别控件、读取消息、发送回复。
2. AI 运行时层
   主要由 `wechat_ai/` 提供，负责决定回复时要带什么上下文、要加载什么画像、要检索什么知识、要不要带入记忆，以及如何记录调试事件。

简化后的链路如下：

```text
Windows 微信界面
-> pywechat / pyweixin 自动化层
-> wechat_ai 运行时
-> MiniMax provider
-> 回复文本
-> 自动化发送
```

## 核心模块

### `wechat_ai/wechat_runtime.py`

这是当前运行时的总协调入口，职责包括：

- 初始化运行时目录
- 从环境变量读取配置
- 构建 provider、retriever、profile store、memory store、event logger
- 暴露单聊、群聊、全局轮询三种运行模式
- 在运行时边界保留 fallback 处理
- 在发送回复和 fallback 时记录结构化事件

这个文件本质上是“微信自动化层”和“AI 编排层”之间的边界。

### `wechat_ai/reply_engine.py`

这是一个较薄的模型调用层，职责包括：

- 区分单聊和群聊系统提示词
- 调用 `PromptBuilder` 渲染最终 user prompt
- 调用 provider 的 `complete()` 方法

它不负责完整编排。完整编排由 `reply_pipeline.py` 决定；`reply_engine.py` 只负责把输入转成一次模型调用。

### `wechat_ai/minimax_provider.py`

MiniMax 的 provider 适配器，职责包括：

- 构造 MiniMax 请求 payload
- 处理模型返回结果
- 暴露统一的 `complete(system_prompt, user_prompt, model)` 接口

当前系统仍然是 MiniMax-first，但 provider 相关逻辑已经被限制在较小边界内，后续替换空间明确。

### `wechat_ai/orchestration/`

这是增强运行时的核心编排包。

`message_parser.py`

- 把原始运行时消息规范化成共享的 `Message` 对象

`context_manager.py`

- 在提示词构建前裁剪和准备最近消息上下文

`prompt_builder.py`

- 构建结构化提示词，目前支持：
  - 助手画像摘要
  - 用户画像摘要
  - 最近会话上下文
  - 检索到的知识片段
  - 可选的会话记忆摘要
  - 当前回复任务

`reply_pipeline.py`

- 负责编排完整的回复前流程：
  - 标准化消息
  - 加载用户画像
  - 加载当前助手画像
  - 准备上下文
  - 执行知识检索
  - 读取记忆摘要
  - 记录结构化事件
  - 调用 reply engine
  - 将会话快照写回 memory

这部分就是当前运行时真正的“思考流水线”。

### `wechat_ai/profile/`

本地画像系统。

`user_profile.py`

- 用户级别的标签、备注、偏好等信息

`agent_profile.py`

- 助手画像，例如目标、风格规则、禁止规则、说明等

`profile_store.py`

- 用户画像和助手画像的 JSON 读写入口

`tag_manager.py`

- 标签标准化与去重工具

`defaults.py`

- 默认 prompt、默认 ID、默认路径等配置基础

这些画像不是简单存储，它们的摘要会被真正注入到提示词中。

### `wechat_ai/rag/`

本地检索增强能力。

`ingest.py`

- 从本地文件加载知识文档

`knowledge_store.py`

- 规范化知识文档与索引数据结构

`chunker.py`

- 将知识文档切分成可检索片段

`embeddings.py`

- 嵌入抽象接口，以及本地测试用的 fake embeddings

`retriever.py`

- 基于本地索引进行相似度检索

`reranker.py`

- rerank 抽象，目前默认 no-op

当前这层是本地优先、文件优先的实现，后面可以替换成更强的嵌入与检索后端。

### `wechat_ai/memory/`

轻量记忆层。

`memory_store.py`

- 按聊天维度保存本地记忆文件
- 当前存储内容包括：
  - 最近会话快照
  - 长期摘要文本
  - 最后更新时间

`conversation_memory.py`

- 会话快照数据结构

`summary_memory.py`

- 摘要数据结构

当前行为是：

- 有记忆摘要时会把它注入提示词
- 每次成功生成回复后，会追加一次会话快照
- 摘要生成仍然是手动/占位驱动，而不是自动更新

### `wechat_ai/logging_utils.py`

结构化可观测性基础模块。

- 提供 append-only JSONL logger
- 使用 UTC 时间戳
- 提供事件读取与 tail 辅助函数
- 提供 inspection 脚本可复用的格式化能力

当前日志事件包括：

- `message_received`
- `profile_loaded`
- `retrieval_completed`
- `prompt_built`
- `model_completed`
- `fallback_used`
- `message_sent`

### `wechat_ai/paths.py`

统一的数据目录布局。

- `wechat_ai/data/users`
- `wechat_ai/data/agents`
- `wechat_ai/data/knowledge`
- `wechat_ai/data/memory`
- `wechat_ai/data/logs`

同时提供启动时创建这些目录的 bootstrap 能力。

## 运行时数据流

当前回复链路可以概括为：

```text
微信收到消息
-> wechat_runtime 判断会话和运行模式
-> reply_pipeline 标准化消息
-> profile store 加载用户/助手画像
-> context manager 裁剪上下文
-> retriever 检索知识
-> memory store 读取记忆摘要
-> prompt builder 渲染结构化提示词
-> MiniMax provider 生成回复
-> reply pipeline 记录完成事件并写入记忆快照
-> wechat_runtime 通过自动化层发送回复
-> runtime 记录 message_sent 或 fallback_used
```

更具体地说：

1. `wechat_runtime.py` 从 `pyweixin` 侧拿到消息文本和会话信息
2. 它构造一个统一的 `Message`
3. `ReplyPipeline.generate_reply()` 完成编排
4. `ReplyEngine` 拼装最终提示词并调用 MiniMax
5. 运行时再通过微信自动化层把回复发送出去

## 本地存储布局

当前运行时采用文件型本地存储。

### 画像

- 用户画像保存在 `wechat_ai/data/users/`
- 助手画像保存在 `wechat_ai/data/agents/`

画像文件是 JSON，缺失时会按默认值自动创建。

### 知识库

- 本地知识索引保存在 `wechat_ai/data/knowledge/`
- 当前默认索引文件是 `local_knowledge_index.json`

### 记忆

- 每个聊天会话的记忆文件保存在 `wechat_ai/data/memory/`
- 文件名由 `chat_id` 规范化后生成

### 日志

- 结构化运行事件追加到 `wechat_ai/data/logs/runtime_events.jsonl`

## 运行脚本

当前主要运行入口在 `scripts/` 下。

### 执行脚本

- `run_minimax_friend_auto_reply.py`
- `run_minimax_group_at_reply.py`
- `run_minimax_global_auto_reply.py`

这些脚本都会：

- 做 COM/bootstrap 初始化
- 从环境变量构建 `WeChatAIApp`
- 支持 `--debug`
- 输出 JSON 结果摘要

### 知识库脚本

- `ingest_knowledge.py`
- `rebuild_index.py`

### 调试脚本

- `show_recent_logs.py`
- `show_memory_summary.py`
- `test_prompt_preview.py`

## 可观测性与调试路径

当前排障流程是本地优先、文件优先的。

### 当你感觉运行不对劲时

1. 用 `--debug` 启动运行脚本
2. 查看最近结构化日志
3. 查看对应聊天的记忆摘要
4. 如果怀疑是提示词问题，再跑 prompt preview

推荐命令：

```powershell
py -3 scripts\show_recent_logs.py --limit 20
py -3 scripts\show_memory_summary.py --chat-id friend_demo
py -3 scripts\test_prompt_preview.py
```

### 当前日志主要帮助回答什么问题

- 消息有没有进入 pipeline
- 画像有没有加载
- 检索有没有执行
- prompt preview 大概是什么样
- 模型有没有正常完成
- 有没有进入 fallback
- 回复是否已经发送

## 测试版图

当前 `scripts/` 下已经有较完整的 `wechat_ai` 测试面。

### 核心运行时与偏集成单测

- `test_wechat_ai_unit.py`
- `test_wechat_ai_pipeline_unit.py`
- `test_wechat_ai_reply_pipeline_unit.py`

### 提示词与编排测试

- `test_wechat_ai_prompt_builder_unit.py`
- `test_wechat_ai_orchestration_context_unit.py`

### 画像测试

- `test_wechat_ai_profile_models_unit.py`
- `test_wechat_ai_profile_config_unit.py`
- `test_wechat_ai_profile_store_unit.py`

### RAG 测试

- `test_wechat_ai_rag_chunking_unit.py`
- `test_wechat_ai_rag_loading_unit.py`
- `test_wechat_ai_rag_retrieval_unit.py`

### 路径、基础与工具测试

- `test_wechat_ai_models_unit.py`
- `test_wechat_ai_paths_unit.py`
- `test_wechat_ai_foundation_smoke.py`
- `test_wechat_ai_observability_scripts_unit.py`
- `test_prompt_preview.py`

这些测试已经能较好覆盖增强运行时，但它们仍然以本地、合成输入和隔离验证为主。真正长时间运行的微信 live 验证仍然属于后续稳定性建设范围。

## 架构上的优势

当前架构已经有几个明显优点：

- 编排边界比早期清晰很多
- 状态不再只在内存里，而是有文件型持久化
- 提示词链路可检查、可预览
- 调试不依赖真实微信会话也能看到不少运行时状态
- 核心模块已经有明确测试覆盖

## 当前架构上的限制

当前设计仍然是轻量实现，因此还存在这些限制：

- 记忆摘要还不能自动更新
- 检索后端仍然偏本地开发态
- 可观测性目前是 append-only JSONL，而不是更强的指标/仪表盘体系
- 真实 Windows 微信长时间运行下的稳定性还需要更多验证

这些限制对应的后续工作，已经在 [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md) 中按路线图列出。
