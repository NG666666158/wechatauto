# 微信自动回复桌面应用壳设计

## 目标

基于现有 `pywechat` / `pyweixin` / `wechat_ai` 内核，补一层适合桌面前端对接的应用服务层。第一版不直接实现完整前端，也不在这一轮完成完整 Windows 打包，而是把首页、消息、设置三类页面需要的后端接口边界先稳定下来，并新增“拖拽文件导入本地知识库并重建向量索引”的真实能力。

这层设计要满足两个要求：

1. 后续你把前端代码接进来时，可以直接调用稳定的 Python 服务接口，不必重新拆运行时内核。
2. 当前就能先把知识库拖拽导入、索引状态查看、基础运行状态查询这些真实功能跑起来。

## 范围

### 本轮实现

- 新增桌面应用服务层，统一封装：
  - 首页状态
  - 消息页会话/消息/建议回复
  - 设置页读取与更新
  - 客户页预留接口
  - 守护状态控制接口预留
- 新增知识库导入模块：
  - 接收前端拖拽后的本地文件路径
  - 复制到 `wechat_ai/data/knowledge/uploads/`
  - 提取文本并归一化为知识文档
  - 重建本地 JSON 索引
  - 返回文件列表、索引状态、最近构建结果
- 新增覆盖这些能力的单测和脚本级验证

### 本轮不做

- 不做完整桌面前端
- 不做系统托盘、全局热键、开机自启
- 不做真正的后台守护进程管理器
- 不做完整 CRM 客户管理页面
- 不做生产级 PDF / DOCX 解析链路，但要预留提取器接口

## 推荐方案

采用“应用服务层 + 可扩展知识导入器”方案。

### 方案 A：直接让前端调用现有 runtime

优点：
- 改动最少

缺点：
- `wechat_runtime` 偏运行时协同，不适合页面级调用
- 页面状态、设置、知识库管理、客户审核接口会散落在不同模块
- 前端后续会强依赖底层实现细节

### 方案 B：新增独立 HTTP 服务

优点：
- 对接前端最直接

缺点：
- 当前前端代码还没进仓，过早锁死 HTTP/进程模型收益不大
- 会把接口协议、生命周期管理、守护进程管理一次性叠加进来

### 方案 C：新增 Python 应用服务层

优点：
- 先把接口语义稳定下来
- 后续可被 Electron / Tauri / PySide 前端直接嵌入调用，也可以再包成 HTTP 层
- 与现有 `wechat_ai` 内核边界清晰，风险最低

缺点：
- 前端接入时还需要再加一层桥接

本轮采用方案 C。

## 架构

新增 `wechat_ai/app/` 目录，作为桌面端后端协议层。

### `wechat_ai/app/models.py`

定义页面和接口共享的数据模型，至少包含：

- `AppStatus`
- `DaemonControlState`
- `ConversationListItem`
- `ConversationMessageItem`
- `ReplySuggestion`
- `SettingsSnapshot`
- `KnowledgeFileRecord`
- `KnowledgeIndexStatus`
- `CustomerRecord`

这些模型的职责是稳定前端对接字段，避免页面直接消费底层 `Message`、`UserProfile`、`MemoryRecord` 等内部结构。

### `wechat_ai/app/settings_store.py`

负责桌面应用层面的设置读写，保存到新的 `wechat_ai/data/app/desktop_settings.json`。它只管理页面配置，不替代现有环境变量和 profile store。

首批设置包括：

- 自动回复开关
- 工作时间
- 回复风格标签
- 新客户自动建档开关
- 敏感消息人工审核开关
- 知识库索引参数

### `wechat_ai/app/knowledge_importer.py`

负责拖拽文件导入和索引状态管理。

核心能力：

- 校验拖拽路径是否存在
- 将文件复制到 `wechat_ai/data/knowledge/uploads/`
- 按扩展名选择文本提取器
- 生成标准 `KnowledgeDocument`
- 触发重建索引
- 返回导入结果和索引状态

提取器采用注册表设计：

- 当前真实支持：`.txt`、`.md`、`.json`
- 预留扩展：`.pdf`、`.docx`

这样后续接更强的文档解析时，不需要改前端接口。

### `wechat_ai/app/service.py`

桌面应用总服务，向前端暴露稳定方法：

- `get_app_status()`
- `start_daemon()`
- `pause_daemon()`
- `stop_daemon()`
- `list_conversations()`
- `get_conversation_messages(conversation_id)`
- `suggest_reply(conversation_id, message_text)`
- `send_reply(conversation_id, text)`
- `handoff_conversation(conversation_id)`
- `get_settings()`
- `update_settings(patch)`
- `list_customers()`
- `get_customer(customer_id)`
- `list_identity_drafts()`
- `list_identity_candidates()`
- `import_knowledge_files(paths)`
- `list_knowledge_files()`
- `get_knowledge_status()`
- `rebuild_knowledge_index()`

其中：

- 首页、设置、知识库接口做真实实现
- 消息和客户页接口先做“可对接骨架”
- 发送消息、人工接管、守护启停先返回结构化占位结果，后续再接真实后台管理器

## 数据流

### 页面读取

```text
桌面前端
-> app.service
-> settings_store / identity_admin / profile_store / memory_store / logs / rag index
-> 页面 DTO
```

### 拖拽入库

```text
桌面前端拖拽文件
-> app.service.import_knowledge_files(paths)
-> knowledge_importer 复制文件到 uploads
-> 提取文本并归一化文档
-> 复用现有 chunker + embeddings + build_index
-> 写入 local_knowledge_index.json
-> 返回导入结果与索引状态
```

## 页面映射

### 首页

真实提供：

- 微信连接状态
- 自动回复状态
- 今日统计占位
- 待处理数量占位
- 守护状态

### 消息

第一版提供接口骨架：

- 会话列表
- 指定会话消息列表
- AI 建议回复
- 发送 / 重生成 / 人工接管占位

### 设置

真实提供：

- 基础设置读写
- 回复策略相关应用层设置
- 知识库文件列表
- 索引状态
- 重建入口

### 客户

本轮只预留：

- 客户列表 DTO
- 客户详情 DTO
- draft / candidate 查询

底层直接复用现有 identity admin。

## 错误处理

- 无效拖拽路径：返回逐文件失败原因，不中断整个批次
- 不支持的文件类型：记录为 `unsupported`
- 文本提取失败：记录为 `failed`
- 索引重建失败：保留已复制文件，返回错误状态
- 占位接口：显式返回 `not_implemented`，避免前端误判为成功

## 测试

新增测试覆盖：

- 设置读写默认值和 patch 更新
- 知识库拖拽导入成功路径
- 不支持文件类型和缺失文件路径
- 索引状态计算
- 应用服务首页/设置/知识库接口
- 消息/客户页占位接口结构稳定性

## 兼容性

- 不破坏现有脚本入口
- 不改已有 RAG 检索协议
- 不改 `wechat_runtime` 主循环
- 新增目录应由 `paths.bootstrap_data_dirs()` 一并创建

## 后续扩展位

- 将 `app.service` 再包装为 HTTP / IPC 服务
- 接入真实后台守护进程
- 接入托盘、定时启停、人工接管状态机
- 扩展 PDF / DOCX 提取器
- 把消息页占位接口接到真实会话缓存和 runtime 事件流
