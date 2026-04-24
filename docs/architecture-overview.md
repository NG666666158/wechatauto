# 架构总览

## 文档目的

这份文档说明当前仓库的真实结构、模块边界、数据流和存储布局。

如果你第一次进入这个项目，建议先看：

1. [README.md](/C:/github/pywechat/pywechat-main/pywechat-main/README.md)
2. [docs/architecture-overview.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/architecture-overview.md)
3. [docs/desktop-app-backend.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/desktop-app-backend.md)
4. [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)

## 系统分层

当前项目可以分成四层：

1. 微信桌面自动化层
2. AI 运行时编排层
3. 数据与知识层
4. 桌面客户端服务层

简化后的链路是：

```text
微信桌面 UI
-> pywechat / pyweixin
-> wechat_ai.wechat_runtime
-> orchestration.reply_pipeline
-> provider / knowledge / memory / profiles / self_identity
-> 回复文本
-> pyweixin 发送
```

## 一层：微信桌面自动化层

主要目录：

- `pywechat/`
- `pyweixin/`

职责：

- 打开微信窗口
- 识别聊天界面与控件
- 读取消息
- 检测未读
- 发送回复

这是整个系统与真实微信交互的底层。

## 二层：AI 运行时编排层

主要目录：

- `wechat_ai/`

### `wechat_ai/wechat_runtime.py`

这是运行时总入口，负责：

- 初始化路径与目录
- 读取环境配置
- 组装 provider、retriever、memory、profile、identity 等依赖
- 暴露单聊、群聊、全局轮询等运行模式
- 管理守护主循环、事件日志与回退逻辑
- `stop_event` 已接入本地守护控制层与全局自动回复主循环，停止时会停止继续扫描新消息，并在退出前 flush pending 消息

### `wechat_ai/orchestration/`

这是回复前编排的核心层。

主要模块：

- `message_parser.py`
- `context_manager.py`
- `prompt_builder.py`
- `reply_pipeline.py`

职责：

- 标准化消息
- 整理上下文
- 拼装 prompt
- 加载画像、自我身份、记忆与知识
- 调用回复引擎
- 记录事件与写回 memory

### `wechat_ai/reply_engine.py`

职责：

- 负责把编排结果转成一次模型调用
- 连接 `PromptBuilder` 与 provider

### `wechat_ai/minimax_provider.py`

职责：

- 屏蔽 MiniMax API 细节
- 暴露统一 `complete(...)` 接口

## 三层：数据与知识层

### 1. 画像与身份

主要目录：

- `wechat_ai/profile/`
- `wechat_ai/identity/`
- `wechat_ai/self_identity/`

职责：

- 用户画像管理
- 助手画像管理
- 用户身份识别与候选归并
- 分层自我身份管理

当前自我身份采用三层模型：

1. 全局身份
2. 关系身份
3. 用户级覆盖身份

### 2. RAG 与知识库

主要目录：

- `wechat_ai/rag/`

职责：

- 文档导入
- 文本抽取
- 文档切块
- 索引构建
- 检索与 rerank 抽象

当前已支持：

- `.txt`
- `.md`
- `.json`
- `.pdf`
- `.docx`
- 图片 OCR

### 3. 记忆

主要目录：

- `wechat_ai/memory/`

职责：

- 按会话保存轻量 memory
- 保存会话快照
- 注入摘要型记忆

### 4. 日志与路径

主要模块：

- `wechat_ai/logging_utils.py`
- `wechat_ai/paths.py`

职责：

- 写入结构化 JSONL 事件日志
- 统一数据目录布局
- 提供初始化和工具脚本依赖的路径入口

## 四层：桌面客户端服务层

主要目录：

- `wechat_ai/app/`
- `wechat_ai/server/`

核心入口：

- [wechat_ai/app/service.py](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/service.py)
- [wechat_ai/server/main.py](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/server/main.py)

这一层的目标是：

- 给桌面客户端提供稳定边界
- 屏蔽底层运行时实现细节
- 提供适合前端调用的数据结构

`wechat_ai/app/` 提供客户端业务 facade，`wechat_ai/server/` 提供本地 HTTP API 入口。第一版服务层已经使用 `/api/v1` 前缀，并提供 `ping`、`health`、统一响应结构、错误码和 `trace_id`。

当前已经具备的能力包括：

- app 状态读取
- daemon 状态控制
- 设置读写
- 客户列表与客户详情聚合
- identity draft / candidate 列表
- 自我身份管理
- 知识库导入与状态查询
- 联网扩库入口

仍未完全闭环的接口主要是：

- `suggest_reply(...)`
- `send_reply(...)`

## 数据目录布局

默认运行数据位于：

- `wechat_ai/data/users/`
- `wechat_ai/data/agents/`
- `wechat_ai/data/self_identity/`
- `wechat_ai/data/knowledge/`
- `wechat_ai/data/memory/`
- `wechat_ai/data/logs/`
- `wechat_ai/data/app/`

其中：

- 用户画像在 `users/`
- 助手画像在 `agents/`
- 自我身份在 `self_identity/`
- 知识库索引和上传文件在 `knowledge/`
- memory 在 `memory/`
- 运行事件日志在 `logs/`
- 桌面端设置和 daemon 状态在 `app/`

## 真实回复数据流

回复链路可以概括为：

```text
收到微信消息
-> wechat_runtime 识别会话与运行模式
-> reply_pipeline 标准化消息
-> 加载用户画像 / 助手画像 / 自我身份
-> 裁剪上下文
-> 检索知识
-> 读取 memory
-> 构建 prompt
-> provider 生成回复
-> 写入日志与 memory
-> 通过 pyweixin 发送
```

## 调试路径

调试时建议优先看：

```powershell
py -3 scripts\show_recent_logs.py --limit 20
py -3 scripts\show_memory_summary.py --chat-id friend_demo
py -3 scripts\test_prompt_preview.py
py -3 scripts\show_desktop_app_snapshot.py
```

真实微信相关检查：

```powershell
py -3 scripts\test_pyweixin_smoke.py
py -3 scripts\test_pull_messages_regression.py
```

## 当前架构判断

当前架构的优点：

- 模块边界已经比较清晰
- 画像、身份、自我身份、memory、RAG 已经进入统一编排链路
- 数据目录已经集中
- 真实运行、调试、测试三条路径都已有入口

当前架构仍需补强的点：

- 长时守护稳定性
- 桌面客户端完整闭环
- 更细的安全边界
- 更完整的运维策略
