# WeChatAuto 客户端化与后端重构执行计划

## 0. 文档定位

这不是一份“从零重写项目”的规划，而是一份：

`基于当前仓库真实进度，对后续服务化、客户端化、稳定性建设进行增量重构的执行计划。`

这份文档的目标是解决两个问题：

1. 当前项目已经做到哪一步，哪些能力不应该重写。
2. 后续怎样重构，才能既不破坏现有可运行链路，又能顺利过渡到桌面客户端。

## 1. 当前项目真实现状

结合本地代码与近期联调结果，当前项目已经具备：

- 微信单聊自动回复
- 微信群聊 `@` 自动回复
- 全局未读轮询与聚合回复
- 多条消息顺序修正与回归测试
- 用户身份识别
- 分层自我身份
  - 全局
  - 关系
  - 用户覆盖
- 用户画像 / 助手画像管理
- 本地 memory store
- 本地知识库导入与检索
- 文档导入
  - `txt`
  - `md`
  - `json`
  - `pdf`
  - `docx`
  - 图片 OCR
- 联网扩库基础能力
- 结构化 JSONL 日志
- 守护模式、心跳、backoff、首次启动引导
- 桌面客户端后端壳层 `DesktopAppService`

当前还没有完全做完的关键点：

- 桌面客户端前后端完整接线
- 消息页真实回复闭环
- 统一本地 API 服务层
- 更稳的启停控制与状态查询
- 长时间真实微信运行稳定性
- 更完整的运维与数据保留策略

## 2. 重构原则

本次重构必须遵守以下原则：

1. 不重写 `wechat_ai/` 的核心运行时链路。
2. 不重写 `pywechat/` 和 `pyweixin/` 的现有底层自动化能力。
3. 不删除现有 `scripts/` 调试与运行入口。
4. 不先做大搬家，不先强行统一目录，不先引入重型基础设施。
5. 先服务化收口，再客户端化接入。
6. 先把真实可运行链路稳住，再谈数据库和性能优化。
7. 任何新抽象都必须复用现有代码，而不是复制一套新的业务逻辑。

## 3. 不建议做的事情

为了避免重复建设和过度重构，下面这些事情当前不建议优先做：

- 不建议立即把整个项目整体迁到全新的 `backend/ frontend/ data/` 总目录结构。
- 不建议先上 Redis、Celery、RabbitMQ、Kafka、微服务。
- 不建议第一阶段就把 JSON / 文件存储全部迁移到 SQLite。
- 不建议先做完整 EventBus / TaskManager / Circuit Breaker 大系统。
- 不建议为了“架构整齐”而拆散当前已经可运行的 `wechat_ai/app/service.py` 和 `wechat_ai/wechat_runtime.py`。

这些能力不是不能做，而是应该后移。

## 4. 总体目标架构

后续推荐的目标架构是：

```text
桌面客户端前端
-> 本地 HTTP / WebSocket API
-> 轻量服务层（复用 DesktopAppService / RuntimeManager）
-> wechat_ai runtime
-> pyweixin / pywechat
-> 微信桌面客户端
```

其中最关键的一点是：

`服务层是对现有运行时的封装，不是重新实现一套新的运行时。`

## 5. 推荐目录策略

当前不建议立刻进行大规模目录搬迁。

推荐采用“增量新增”的方式：

```text
desktop_app/
  frontend/

wechat_ai/
  app/
  server/                # 新增，本地 API 服务层
    main.py
    api/
    schemas/
    services/
    core/

pywechat/
pyweixin/
scripts/
docs/
```

这样做的好处：

- 不破坏当前导入路径
- 不影响既有脚本
- 不需要立刻修改大量文档和测试
- 能用最小代价把客户端能力接上

后续如果真的需要独立出 `backend/`，可以等服务层稳定后再做。

## 6. 技术栈建议

### 6.1 后端服务层

推荐：

- `FastAPI`
- `Uvicorn`
- `Pydantic`
- `ThreadPoolExecutor` 或标准线程模型
- `SQLite` 作为后续元数据层
- `JSONL` 保留为原始事件日志

可选增强：

- `APScheduler`
- `diskcache`
- `Tenacity`
- `Alembic`

当前不建议引入：

- Redis
- Celery
- RabbitMQ
- Kafka
- Kubernetes
- PostgreSQL
- MySQL
- Qdrant Server
- Milvus Server

### 6.2 客户端技术栈

当前推荐：

- 前端继续使用现有 `desktop_app/frontend`
- 客户端壳层优先考虑 `Electron`

原因：

- 当前阶段核心目标是尽快形成可联调桌面版
- Electron 对本地后端进程拉起、调试和问题定位更直接
- 等功能真正稳定后，再评估 Tauri 轻量化

## 7. 分阶段执行计划

### 阶段 A：本地 API 服务骨架

目标：

在不破坏现有结构的前提下，新增一个统一本地 API 服务入口。

建议新增：

```text
wechat_ai/server/main.py
wechat_ai/server/api/
wechat_ai/server/services/
wechat_ai/server/schemas/
wechat_ai/server/core/
```

第一批 API 只做最小集合：

- `GET /api/ping`
- `GET /api/health`
- `GET /api/runtime/status`
- `POST /api/runtime/start`
- `POST /api/runtime/stop`
- `GET /api/config`
- `POST /api/config`
- `GET /api/logs/recent`

要求：

- 第一版直接复用现有 `DesktopAppService`
- 不允许复制一套新的客户、知识库、身份逻辑
- 不影响现有脚本命令运行

验收标准：

- 能正常启动 FastAPI
- `/docs` 可用
- 前端能请求本地服务
- 现有脚本仍可独立运行

### 阶段 B：RuntimeManager 收口

目标：

把现在分散在脚本里的守护启动逻辑，统一收口成可控运行器。

新增职责：

- 启动任务
- 停止任务
- 重启任务
- 查询状态
- 防止重复启动
- 记录最后错误
- 管理 stop_event

第一版状态机只保留：

- `idle`
- `starting`
- `running`
- `stopping`
- `stopped`
- `error`

第一版只支持模式：

- `global`

后续再加：

- `friend`
- `group_at`

验收标准：

- 前端或 Postman 可调用 start / stop
- 不会启动多个重复守护实例
- 可正常停止
- 异常可记录为 `error`

### 阶段 C：配置中心与路径收口

目标：

把现有环境变量驱动的配置，逐步收口为本地可读写配置。

注意：

- 当前不要求彻底替代环境变量
- 第一阶段应采用“文件配置覆盖 + 环境变量兜底”的兼容策略

建议配置路径：

- 开发态：`wechat_ai/data/app/desktop_settings.json`
- 后续客户端态：迁移到用户 `AppData`

第一版配置至少覆盖：

- model
- runtime
- reply
- safety
- app behavior

要求：

- 前端可读写
- 与当前 `DesktopSettingsStore` 兼容
- 不因配置重构影响现有运行链路

### 阶段 D：日志、健康检查、基础运维接口

目标：

让前端先能看到“系统是否健康、最近做了什么、哪里出错了”。

第一批能力：

- recent logs API
- health API
- runtime status API

第二批再补：

- WebSocket 实时日志
- WebSocket runtime 状态推送

这里建议先做 HTTP，再做 WebSocket，原因是：

- 调试更简单
- 首批客户端页面并不强依赖实时推流
- 可以先把正确性做稳

### 阶段 E：客户端第一批真实页面接口

目标：

优先接通最接近当前后端完成度的页面。

推荐顺序：

1. 首页
2. 设置页
3. 客户页
4. 知识库页
5. 消息页

其中消息页必须单列成专项，因为当前最难点在这里。

首页需要：

- runtime status
- health
- daemon start / stop
- 基础统计

设置页需要：

- get/update settings
- 安全策略
- 启动行为

客户页需要：

- customer list
- customer detail
- identity drafts
- identity candidates
- self identity 管理接口

知识库页需要：

- import knowledge files
- knowledge status
- search knowledge
- build web knowledge from documents

消息页需要后续专项补齐：

- `suggest_reply(...)`
- `send_reply(...)`
- 会话级暂停
- 人工接管

### 阶段 F：稳定性增强

目标：

在不推翻当前守护主循环的前提下，增强真实运行稳定性。

优先做：

- timeout
- retry
- per-session pause
- human takeover
- whitelist / blacklist
- 更清晰的异常分层

后做：

- debounce
- 复杂限流
- 更重的状态恢复机制

说明：

这里不建议先造一个很重的 EventBus / TaskManager 体系。
如果后续确实出现多个并行后台任务、日志订阅、索引重建任务互相影响的问题，再引入也不晚。

### 阶段 G：SQLite 元数据层

目标：

引入轻量数据库，但只管理“结构化元数据”，不立刻接管全部业务真源。

第一批建议进入 SQLite 的数据：

- app config mirror
- runtime task state
- session state
- knowledge file metadata
- knowledge chunk metadata

当前不建议第一批迁移：

- 用户画像主数据
- 自我身份主数据
- memory 主数据

这些仍然保留当前 JSON / 文件为真源。

原因：

- 当前项目已经有稳定文件型路径
- 现在最大瓶颈不是文件存储本身
- 太早迁移会明显增加联调风险

### 阶段 H：RAG 优化

目标：

在当前知识库可用的基础上做增强，而不是推翻重建。

建议路线：

第一步：

- 保持现有本地检索链路
- 增加 metadata 管理
- 增加更好的启用/禁用与来源追踪

第二步：

- 再考虑 `FAISS` 或 `Chroma`

第三步：

- 只有在明确需要时，才考虑云端或独立向量服务

### 阶段 I：客户端包装与交付

目标：

把“前端 + 本地后端”打包成真实桌面客户端。

建议：

- 原型期：继续前端开发 + 独立 Python 服务
- 首次打包：Electron + backend service
- 稳定后再考虑更轻量的 Tauri

客户端需要具备：

- 启动本地后端
- 检测后端是否已运行
- 托盘
- 最小化到后台
- 开机自启
- 打开日志目录
- 打开数据目录

## 8. 开发优先级

### P0：必须先做

- 本地 API 服务骨架
- `/api/v1` 路由前缀
- 统一 API 响应与错误码
- RuntimeManager
- stop_event 停止机制
- stop_event 检查点覆盖轮询、sleep/backoff、消息聚合、模型调用前、发送前、重试前
- 配置中心兼容收口
- 配置优先级：`desktop_settings.json` > 环境变量 > 默认配置
- 统一健康检查
- 基础日志 API
- 统一路径策略

### P1：稳定性与前端基础接入

- 首页 / 设置页 / 客户页 / 知识库页 API 接入
- 基础 human takeover
- per-session pause
- whitelist / blacklist
- timeout / retry
- 更清晰的异常输出
- 微信 UI 自动化稳定性专项
- 基础数据保留与隐私策略

当前进度：

- 已完成首页、设置、客户、自我身份、知识库、日志、隐私、微信环境检查的第一批 HTTP API。
- 已完成 `runtime/restart`，前端可以用单接口做守护重启。
- 已完成会话级控制接口：人工接管、暂停、白名单、黑名单。
- 已完成隐私策略读取/更新与 runtime log 保留清理入口；memory 已有快照上限，保留策略入口会继续做轻量裁剪。
- 消息页真实 `suggest/send` 闭环、发送后成功判定、WebSocket 推送仍保留到 P2。

### P2：消息页与产品闭环

- suggest reply
- send reply
- 会话状态管理
- 更完整的日志可视化
- WebSocket 推送
- 发送前内容校验
- 发送后成功判定

当前进度：

- `P2-1` 已完成第一版会话数据层：`list_conversations`、`get_conversation`、`record_conversation_message`，并通过 `/api/v1/conversations` 暴露给前端。
- `P2-2` 已完成第一版 AI 建议回复接口：`POST /api/v1/conversations/{conversation_id}/suggest`，服务层可注入 `ReplyPipeline` 生成真实建议；未配置 pipeline 时仍返回占位状态，避免无模型配置时崩溃。
- `P2-3` 已完成第一版发送前校验：空文本、人工接管、会话暂停、黑名单会在 `send_reply` / `/send` 阶段被阻断，并向前端返回 `reason_code`。
- `P2-4` 已完成第一版真实发送适配器：`send_reply` 通过校验后可调用注入的 sender，或在 `real_send_enabled=true` 时调用 pyweixin 发送适配器；成功后写入本地会话缓存，失败返回 `SEND_FAILED` 且不写出站消息。
- 真实微信消息来源写入会话缓存、发送后 UI 成功判定、WebSocket 推送仍待后续 P2 子阶段完成。

### P3：SQLite 与 RAG 增强

- SQLite 元数据层
- 知识库元数据管理
- 检索优化
- 索引后台化

### P4：桌面交付

- Electron 壳层
- backend 打包
- 托盘与静默后台
- 安装包
- 自动更新

## 9. 当前最小可行闭环

后续最小闭环不应该定义成“完整客户端”，而应该定义成：

1. 前端可请求本地 FastAPI
2. 前端可启动 / 停止当前全局守护
3. 前端可查看 runtime 状态
4. 前端可修改配置
5. 前端可查看最近日志
6. 前端可管理客户、身份、自我身份、知识库

只要这 6 点打通，就已经形成：

`当前项目从脚本系统到本地桌面服务系统的第一阶段闭环。`

## 10. 与当前代码的衔接要求

后续所有重构都必须遵守以下衔接要求：

- `DesktopAppService` 作为第一阶段服务层底座，优先复用
- `wechat_runtime.py` 保持现有主链路不被拆碎
- `scripts/` 继续保留
- `wechat_ai/data/` 继续作为开发态数据目录
- 文档、测试、真实联调三者同步推进

## 11. 推荐执行顺序

接下来最推荐的顺序是：

1. 新增本地 FastAPI 服务骨架
2. 先补 `/api/v1`、统一错误响应、基础错误码
3. 做 RuntimeManager + stop_event + status
4. 接 config / health / logs，并落实配置优先级
5. 接 customers / self identity / knowledge
6. 建立微信 UI 自动化稳定性检查清单
7. 单独做消息页真实闭环
8. 补 human takeover、per-session pause、白名单、黑名单
9. 补数据保留、隐私、日志清理、memory 裁剪策略
10. 再做 SQLite 元数据层
11. 最后再做客户端包装

## 12. 最终目标

最终目标不是把当前仓库改造成“很漂亮但难落地的大架构”，而是：

`在保留当前可运行后端主链路的基础上，逐步收口成一个可被桌面客户端稳定调用、可观测、可控制、可交付的本地微信 AI 客服系统。`

## 13. 需要额外补充的风险控制项

### 13.1 服务边界

FastAPI API 层只负责请求响应和参数校验。
DesktopAppService 负责复用现有桌面端业务能力，例如设置、客户、知识库、身份管理。
RuntimeManager 只负责自动回复守护任务的生命周期管理，包括 start、stop、restart、status。
wechat_runtime.py 保持现有 AI 回复主链路，不直接承接前端 API。
scripts/ 继续作为命令行调试入口。

### 13.2 stop_event 检查点

stop_event 不应只在主循环外层检查，至少需要在以下位置检查：

1. 每轮轮询开始前；
2. 每次 sleep/backoff 前后；
3. 消息聚合等待期间；
4. 模型调用前；
5. 消息发送前；
6. 异常重试前。

第一版采用 soft stop：停止后不再扫描和处理新消息，当前已经进入发送阶段的任务允许完成；后续再扩展 force stop。

### 13.3 微信 UI 自动化稳定性专项

需要单独建立微信自动化稳定性检查清单，包括：

1. 微信窗口检测；
2. 微信登录状态检测；
3. 输入框焦点校验；
4. 发送前内容校验；
5. 发送后成功判定；
6. 重复消息去重；
7. 多条消息顺序锁；
8. 微信最小化恢复；
9. 多开微信识别策略；
10. 控件找不到时的降级处理。

### 13.4 API 版本与错误码

本地 API 建议从第一版开始使用 `/api/v1/` 前缀。

统一错误响应格式：

{
  "success": false,
  "code": "WECHAT_WINDOW_NOT_FOUND",
  "message": "未找到微信窗口",
  "detail": "",
  "trace_id": ""
}

第一批错误码建议包括：

- CONFIG_INVALID
- MODEL_API_FAILED
- WECHAT_WINDOW_NOT_FOUND
- WECHAT_NOT_LOGIN
- RUNTIME_ALREADY_RUNNING
- RUNTIME_NOT_RUNNING
- KNOWLEDGE_INDEX_MISSING
- PERMISSION_DENIED
- UNKNOWN_ERROR

### 13.5 配置优先级

客户端场景下采用：

1. desktop_settings.json
2. 环境变量
3. 默认配置

前端设置页需要展示当前配置来源，避免用户不知道配置为什么没有生效。

### 13.6 数据保留与隐私

需要提供基础数据管理策略：

1. runtime logs 默认保留 7 / 14 / 30 天；
2. message memory 每个会话限制最大条数或仅保留摘要；
3. 原始聊天内容默认不长期保存，除非用户开启；
4. API Key 不得明文写入日志；
5. 设置页提供清空日志、清空缓存、清空会话记忆、打开数据目录等功能。

### 13.7 测试与联调要求

测试需要分层：

1. 单元测试：ConfigService、LogService、paths、schemas；
2. 接口测试：ping、health、runtime/status、config、logs；
3. 集成测试：RuntimeManager start/stop，微信操作可 mock；
4. 真实微信联调：Windows + 登录微信 + 测试账号。

真实联调至少包括：

1. 30 分钟冒烟测试；
2. 2 小时稳定性测试；
3. 8 小时长跑测试；
4. 微信关闭/最小化/网络断开/API Key 错误等异常恢复测试。

## 14. 基于风险控制的后续执行路线

第 13 条风险控制项是合理的，建议正式并入执行路线，而不是作为最后才补的附录。

### 14.1 第一批：服务边界与 API 契约

优先级：P0

目标：

- 确定 FastAPI 只做请求响应和参数校验。
- `DesktopAppService` 继续作为业务 facade。
- `RuntimeManager` 只负责自动回复守护任务生命周期。
- `wechat_runtime.py` 保持 AI 回复主链路，不直接承接前端 API。
- `scripts/` 保留为命令行调试入口。

必须同时落地：

- `/api/v1` 路由前缀
- 统一响应格式
- 第一批错误码
- `trace_id`
- health / ping

验收标准：

- 前端拿到的所有 API 都有稳定返回结构。
- 失败时不再只返回 Python 异常文本。
- 现有脚本仍能单独运行。

### 14.2 第二批：可停止、可恢复、可观测

优先级：P0

目标：

- `RuntimeManager` 可以稳定 start / stop。
- `stop_event` 不只在最外层检查。
- 日志能解释为什么没有回复、为什么停止、为什么失败。

必须覆盖的 `stop_event` 检查点：

- 每轮轮询开始前
- sleep/backoff 前后
- 消息聚合等待期间
- 模型调用前
- 消息发送前
- 异常重试前

第一版停止策略：

- 默认 soft stop。
- 停止后不再扫描和处理新消息。
- 已进入发送阶段的任务允许完成。
- force stop 后续再扩展。

### 14.3 第三批：真实微信 UI 稳定性专项

优先级：P1

目标：

- 把真实微信窗口侧的不稳定点从现场经验变成明确检查项。

第一批检查项：

- 微信窗口检测
- 登录状态检测
- 输入框焦点校验
- 发送前内容校验
- 发送后成功判定
- 重复消息去重
- 多条消息顺序锁定
- 最小化恢复
- 多开微信识别策略
- 控件找不到时的降级处理

验收标准：

- 每个检查项都有至少一个单测、mock 测试或真实联调记录。
- 真实联调失败时能定位到具体检查项。

### 14.4 第四批：配置、隐私与数据保留

优先级：P1

目标：

- 用户知道配置来源。
- 日志和 memory 不无限膨胀。
- API Key 和敏感内容不进入日志。

配置优先级：

1. `desktop_settings.json`
2. 环境变量
3. 默认配置

第一版数据策略：

- runtime logs 支持 7 / 14 / 30 天保留策略。
- message memory 按会话限制最大条数。
- 原始聊天内容默认不长期保存，除非用户显式开启。
- API Key 不写入日志。
- 设置页后续提供清空日志、清空缓存、清空会话记忆、打开数据目录。

### 14.5 第五批：测试与真实联调门槛

优先级：P1 到 P2

每个阶段完成后都要分层验证：

- 单元测试：配置、日志、路径、schemas。
- 接口测试：ping、health、runtime/status、config、logs。
- 集成测试：RuntimeManager start/stop，微信操作可 mock。
- 真实联调：Windows + 登录微信 + 测试账号。

真实联调分三档：

- 30 分钟冒烟测试。
- 2 小时稳定性测试。
- 8 小时长跑测试。

异常恢复测试至少覆盖：

- 微信关闭
- 微信最小化
- 网络断开
- API Key 错误
- 模型 API 失败
- 控件找不到

P2-7 当前落地：

- 新增 `scripts/check_wechat_real_run_readiness.py`，把真实微信联调门槛收口成可执行清单。
- 脚本只做只读检查和人工提示，无微信环境下也安全退出，不启动/关闭微信，不杀进程。
- 自动/占位检查覆盖微信进程、微信路径、讲述人状态、显示缩放、权限与前台窗口提示。
- 新增 `wechat_ai/app/wechat_window_probe.py`，提供真实窗口只读探测：当前会话、聊天列表、最近可见气泡、输入框可读性。
- 新增 `scripts/probe_wechat_window.py`，微信未运行时安全 `skipped`，微信已登录且主窗口可见时输出真实 UI ready 探测结果。
- 发送后确认已接入 `PyWeixinVisualSendConfirmer`：真实发送开启后，发送器成功返回还需要在最近可见气泡中确认目标回复文本，确认失败不写 outgoing 缓存。
- 人工/后续脚本清单继续覆盖未读顺序、群聊 sender、焦点/最小化恢复和长跑观察。
- 已补 `scripts/test_wechat_real_run_readiness_unit.py`，验证关键检查项输出和 exit 0。
- 后续仍需把焦点恢复、最小化恢复、异常恢复记录逐步升级为半自动联调脚本，并补真实微信长跑观测。

## 15. 调整后的近期执行顺序

结合当前项目进度和第 13 条风险控制，近期建议按下面顺序执行：

### 15.1 当前前后端联调进度快照

截至当前本地版本，前后端联调处在“后端协议基本成型，真实微信闭环继续加固”的阶段：

| 模块 | 当前进度 | 状态 | 下一步 |
| --- | --- | --- | --- |
| 本地 API 服务 | 约 80% | 已有 FastAPI `/api/v1`、统一响应、runtime/settings/dashboard/customers/identity/knowledge/logs/privacy/environment/conversations/controls 等接口 | 补 WebSocket 状态推送和前端字段契约冻结 |
| 桌面运行控制 | 约 70% | RuntimeManager、soft stop、stop_event、心跳、backoff、长期守护主循环已接入 | 接真实桌面客户端托盘控制、ESC/按钮退出、定时启停 UI |
| 消息页闭环 | 约 65% | 会话缓存、建议回复、发送前校验、真实发送适配器、发送后视觉确认第一版已完成 | 前端接 `/conversations`、`/suggest`、`/send`，补人工接管实时状态 |
| 真实微信联调 | 约 55% | 红点 unread 轮询、active 当前窗口增量监听、顺序回归、窗口只读探测、发送后视觉确认已具备 | 做焦点/最小化恢复、长跑观测、真实群聊 sender 压测 |
| 用户身份/自我身份 | 约 75% | 用户画像、候选身份、自我身份全局/关系/用户覆盖、回复链路身份注入已完成 | 前端编辑页、候选合并确认、身份变更审计 |
| 知识库/RAG | 约 70% | 本地导入、PDF/DOCX/图片抽取、索引、检索、联网扩库第一版已完成 | 前端拖拽入库、知识库切换、索引任务进度事件 |
| 日志/隐私/运维 | 约 75% | 结构化日志、脱敏、保留策略、recent/summary/filter API、readiness 脚本已完成 | 日志页面、错误诊断面板、用户可操作清理入口 |
| 前端静态页面 | 约 35% | 页面目录与静态 UI 仍在调整，尚未正式接后端数据 | 等前端代码稳定后按接口逐页接入 |

### 15.2 后续开发流程

接下来建议按“先真实稳定，再前端接入，再客户端化”的顺序走：

1. 真实微信稳定性专项：继续补 active/unread 去重、焦点恢复、最小化恢复、发送后确认失败处理和长跑日志归因。
2. API 契约冻结：把前端会用到的字段整理成固定 schema，避免前端边写边改接口。
3. 前端逐页接入：先首页和设置页，再消息页，随后客户/身份页，最后知识库页。
4. 事件推送：补 WebSocket/SSE，让前端不用轮询就能拿到运行状态、消息队列、日志和知识库任务进度。
5. 桌面客户端壳：接 Electron/Tauri 的托盘、静默后台、ESC 退出、定时启停、开机/手动启动策略。
6. 长跑验收：30 分钟冒烟、2 小时稳定性、8 小时长跑，记录微信窗口、模型、网络、发送确认、数据缓存五类异常。

本轮新增进度：active 当前窗口监听已接入跨来源去重，避免 unread 轮询已处理过的消息在 active 监听中重复排队/重复回复。

### 15.3 分阶段细分计划

#### P3 真实微信稳定性专项

目标：先让真实微信长期监听尽量“不重复、不漏回、能停、能确认、可归因”。

- P3-1 守护链路发送后确认收口。
  - 状态：已完成第一版。
  - 已把 `WeChatAIApp` 主守护链路接入 `send_confirmer`。
  - `from_env()` 默认尝试接入 `PyWeixinVisualSendConfirmer`。
  - 发送确认失败会记录 `message_send_unconfirmed`，并计入 errors，不再计入成功回复。
  - 回归测试：`test_send_reply_reports_error_when_visual_confirmation_fails`、`test_send_reply_counts_reply_after_visual_confirmation_succeeds`。
- P3-2 细粒度 `stop_event` 中断点。
  - 状态：已完成第一层。
  - 已在生成回复前、真实发送前检查 `stop_event`。
  - stop 后普通发送会跳过并记录 `send_skipped_stop_event`；shutdown force flush 保留发送能力。
  - 回归测试：`test_send_reply_skips_generation_when_stop_event_is_set`、`test_send_reply_skips_actual_send_when_stop_event_is_set_after_generation`。
- P3-3 焦点/最小化/输入框 readiness 半自动探测。
  - 状态：已完成第一版。
  - 扩展 `wechat_ai/app/wechat_window_probe.py`，把窗口最小化、当前前台、输入框可编辑、当前会话标题等拆成稳定字段。
  - 扩展 `scripts/probe_wechat_window.py` 和 `scripts/check_wechat_real_run_readiness.py`。
  - `check_wechat_real_run_readiness.py` 已从 `ui_ready_placeholder` 升级为 `ui_ready_probe`，无微信时安全跳过，有微信时做只读控件探测。
  - `probe_wechat_window.py` 文本输出已展示 `window_ready/window_minimized/input_ready/focus_recommendation`。
  - 测试：`py -3 scripts\test_wechat_window_probe_unit.py`、`py -3 scripts\test_probe_wechat_window_script_unit.py`。
- P3-4 active anchor missed 补偿与可观测性。
  - 状态：已完成第一版。
  - 在 anchor 丢失时输出更具体字段：旧锚点、最新锚点、可见项数量、是否疑似滚动/切会话。
  - 保持“不误回旧消息”优先，后续再考虑保守补偿。
  - 当前策略为 `reanchor_without_reply`：重新锚定到最新可见消息，但不回复可见历史消息。
  - 日志字段已包含 `candidate_count`、`first_visible_text`、`latest_visible_text`、`visible_signature_sample`、`diagnosis`。
  - 测试：`py -3 scripts\test_wechat_ai_unit.py`。
- P3-5 群聊 sender 压测与 unread sender 补强。
  - 状态：已完成第一版。
  - unread/group 路径已兼容结构化消息：`text/message/content` + `sender_name/sender/nickname/from`。
  - 当 unread 只返回字符串时，会在打开群聊后从可见消息控件中反查 `Tools.parse_message_content`，尽量补齐真实群成员 sender。
  - sender 识别成功写入 `group_sender_detected`，无法识别时按群名兜底并写入 `group_sender_unresolved`。
  - 新增只读真实探针：`py -3 scripts\probe_wechat_group_sender.py --format json`，用于在当前群聊窗口验证可见消息 sender 解析情况。
  - 回归测试：`test_process_unread_session_passes_structured_group_sender_to_reply_pipeline`、`test_process_unread_session_normalizes_blank_structured_group_sender`、`test_process_unread_session_enriches_string_group_sender_from_visible_items`。
  - 测试：`py -3 scripts\test_wechat_ai_unit.py`。
- P3-6 去重策略升级。
  - 状态：已完成第一版。
  - 已从 `session + source + text` 升级为 sender-aware 语义 key：`chat_type:session + sender + normalized_text`。
  - 朋友会话 sender 固定为会话名；群聊 sender 参与去重，避免不同群成员发送同一句话时被误杀。
  - active/unread 跨来源使用同一语义 key，确保同一群成员同一条消息不会被两个入口重复处理。
  - 保留朋友会话旧 key 兼容，避免旧运行状态或旧单测的手工签名立即失效。
  - 回归测试：`test_group_unread_dedupe_allows_same_text_from_different_sender_later`、`test_active_cross_source_dedupe_skips_same_group_sender_duplicate`、`test_active_cross_source_dedupe_is_group_sender_aware`。
- P3-7 长跑观测与异常归因报告。
  - 状态：已完成第一版。
  - 新增 `scripts/long_run_observer.py`，默认只读汇总 readiness、window probe 和 `runtime_events.jsonl`。
  - 输出 runtime event counts、最近事件、error-like 事件、heartbeat 时间、回复比例、异常计数和诊断建议。
  - 异常归因覆盖 `loop_error`、`message_send_unconfirmed`、`active_anchor_missed`、`fallback_used`、readiness warn/error、window probe not ready。
  - 默认追加 JSONL 到 `wechat_ai/data/logs/long_run_observer.jsonl`，也可用 `--no-write` 只打印。
  - 30 分钟冒烟：`py -3 scripts\long_run_observer.py --target-duration-minutes 30 --format json`。
  - 2 小时稳定性：`py -3 scripts\long_run_observer.py --target-duration-minutes 120 --format json`。
  - 8 小时长跑：`py -3 scripts\long_run_observer.py --target-duration-minutes 480 --format json`。
  - 无微信/CI 单测可用：`--skip-readiness --skip-window-probe`。
  - 测试：`py -3 scripts\test_wechat_ai_observability_scripts_unit.py`。

#### P4 API 契约冻结

目标：前端接入前冻结主要字段，避免边接边改。

- P4-1 API 契约基线清单：整理 endpoint、method、request、response、业务状态码。
  - 状态：已完成第一版。
  - 新增 `scripts/export_api_contract.py`，从 FastAPI OpenAPI 生成契约基线。
  - 输出文件：`docs/api-contract/openapi.snapshot.json`、`docs/api-contract/api-contract.baseline.json`。
  - 当前基线：31 个 `/api/v1` 端点、10 个 schema；大部分 response 仍为 `ApiResponse[dict[str, object]]`，后续 P4-2 收紧。
  - 测试：`py -3 scripts\test_wechat_ai_api_contract_unit.py`、`py -3 scripts\test_wechat_ai_server_unit.py`。
- P4-2 Typed response schemas：把主要 `dict[str, object]` 响应替换为 Pydantic schema。
  - 状态：第二批已完成。
  - 第一批：`runtime/status/start/stop/restart`、`dashboard/summary`、`settings`、`logs/summary`。
  - 已新增 `RuntimeStatusData`、`RuntimeActionData`、`DashboardSummaryData`、`SettingsData`、`LogsSummaryData`。
  - 第二批：`conversations`、`customers`、`identity`、`knowledge`、`privacy`、`environment`、`controls`。
  - 已新增 `ConversationListItemData`、`ConversationDetailData`、`ReplySuggestionData`、`SendReplyResultData`、`CustomerData`、`IdentityDraftData`、`IdentityCandidateData`、`SelfIdentityData`、`KnowledgeStatusData`、`KnowledgeSearchResultData`、`KnowledgeImportResultData`、`WebKnowledgeBuildResultData`、`PrivacyPolicyData`、`RetentionApplyResultData`、`WechatEnvironmentData`、`ConversationControlData`。
  - 已重新导出 `docs/api-contract/openapi.snapshot.json` 和 `docs/api-contract/api-contract.baseline.json`。
  - 当前保留泛型的接口：`ping`、`health`、`logs/recent`，后续可在 P4-5/P4-6 视前端需要继续收紧。
- P4-3 Request schema 冻结：补 settings/privacy/controls/runtime/knowledge 的请求模型和边界测试。
  - `settings.patch` 禁止任意未知字段逐步收紧；先支持当前 UI 需要字段。
  - `privacy.patch` 限定保留天数、日志数量、脱敏开关。
  - `controls.patch` 限定 `human_takeover/paused/whitelisted/blacklisted`。
  - `knowledge.import/web-build` 增加空文件、过大 limit、非法路径格式的 422 测试。
  - 已完成：新增 `SettingsPatchRequest`、`PrivacyPolicyPatchRequest`、`ConversationControlPatchRequest`、`SelfIdentityPatchRequest`，并让 `RuntimeStartRequest` 禁止未知字段；同时将 `knowledge.import/web-build` 的空文件和 `search_limit` 边界纳入统一 `REQUEST_INVALID` 422。
  - 已完成：补充 OpenAPI request schema 冻结测试和接口边界回归测试，重新导出 `docs/api-contract/openapi.snapshot.json` 与 `docs/api-contract/api-contract.baseline.json`。
- P4-4 错误码与业务状态分层：区分 HTTP API 错误和业务阻断状态。
  - HTTP 错误：运行时重复启动、未运行停止、请求校验、配置错误、未知异常。
  - 业务状态：`send_reply` 的 `blocked/not_implemented/sent/unconfirmed/failed` 留在 `data.status`，不滥用 HTTP 500。
  - 输出统一错误码清单给前端。
  - 已完成：新增 `GET /api/v1/errors/catalog`，返回 `http_errors`、`send_reply_statuses`、`send_reply_reason_codes` 三组前端可消费清单。
  - 已完成：补充回归测试，锁定发送前校验阻断仍返回 HTTP 200 + `success=true` + `data.status=blocked`，不进入 `error` 分支。
- P4-5 契约快照测试：新增 OpenAPI/fixture snapshot，防止字段被无意改名。
  - 固化 `docs/api-contract/openapi.snapshot.json`。
  - 测试要求：新增/删除/改名端点时必须显式更新 snapshot。
  - 保持输出排序稳定，减少无意义 diff。
  - 已完成：`scripts/test_wechat_ai_api_contract_unit.py` 新增快照一致性测试，实时生成 OpenAPI/contract 并与 `docs/api-contract/` 内快照比较。
  - 已完成：`scripts/export_api_contract.py --check` 支持只校验不写文件；快照漂移时返回非 0 并提示更新命令。
- P4-6 前端 mock fixtures：输出 dashboard/settings/conversation/send/knowledge/logs 示例 JSON。
  - 目录建议：`desktop_app/frontend/fixtures/api/` 或 `docs/api-contract/fixtures/`。
  - 覆盖 5 个一级页面：首页、消息、客户、知识库、设置。
  - 每个 fixture 保持真实 `ApiResponse` 外壳：`success/data/error/trace_id`。
  - 已完成：新增 `scripts/export_api_fixtures.py`，导出 23 个 fixture 到 `docs/api-contract/fixtures/`，覆盖首页、消息、客户、知识库、设置所需主要 API。
  - 已完成：新增 fixtures 快照测试和 `--check` 模式，前端联调前可直接校验样例是否与当前后端契约一致。
- P4-7 事件推送契约预留：先冻结事件类型和 payload，再实现 SSE。
  - 事件外壳：`{id,type,timestamp,data,trace_id}`。
  - 事件类型第一批：`runtime.status`、`message.received`、`message.sent`、`knowledge.progress`、`log.event`、`error`。
  - P6 再实现 `GET /api/v1/events` SSE；P4 只冻结 schema 和 fixtures。
  - 已完成：新增 `wechat_ai/server/schemas/events.py` 和 `scripts/export_event_contract.py`，输出 `docs/api-contract/event-contract.json` 作为事件契约基线。
  - 已完成：新增事件契约快照测试，锁定 envelope 字段和首批 6 类事件 payload 结构。

#### P5 前端逐页接入

目标：先接低风险页面，再接真实消息闭环。

- P5-1 前端 API 基建：`apiClient`、`ApiResponse<T>`、base URL、loading/error/empty 组件。
- P5-2 首页接入：dashboard/runtime/logs/environment，启动/停止/重启按钮。
  - 已完成第一版：新增 `desktop_app/frontend/lib/api.ts`，冻结前端 `ApiResponse<T>`、dashboard/runtime/logs/environment 类型和基础 runtime action 方法。
  - 已完成第一版：新增 `components/api-state.tsx` 和前端类型契约测试；首页已改为 client-side 调用 dashboard/runtime/logs/environment，并提供启动/暂停/重启守护动作。
- P5-3 设置页接入：settings/privacy 读写、保存状态、敏感开关二次确认。
  - 已完成第一版：`/settings` 页面接入 `GET/PATCH /settings` 与 `GET/PATCH /privacy/policy`，支持自动回复、工作时间、回复风格、新客户建档、敏感审核、日志/记忆保留、知识库分块等设置读写。
  - 已完成第一版：关闭“敏感消息先审核”时增加二次确认；保存成功和失败均有页面反馈。
- P5-4 消息页只读接入：conversations/detail/control 展示。
  - 已完成第一版：`/messages` 页面接入 `GET /conversations`、`GET /conversations/{conversation_id}` 与会话控制状态展示，支持会话搜索、详情消息流、最近入站消息提示和人工接管/暂停/黑名单只读状态。
  - 已完成第一版：发送输入框、AI 建议发送、重新生成、人工接管按钮保持禁用，避免 P5-5 前误触真实发送链路。
- P5-5 消息页闭环：suggest/send/control patch，处理 blocked/failed/unconfirmed/not_implemented。
  - 已完成第一版：`/messages` 页面接入 `POST /conversations/{conversation_id}/suggest`，可基于最近入站消息生成建议并写入草稿。
  - 已完成第一版：接入 `POST /conversations/{conversation_id}/send`，发送前增加浏览器确认；成功后刷新会话，`blocked/failed/unconfirmed/not_implemented` 等业务状态会展示在页面侧栏，不伪装成成功。
  - 已完成第一版：接入 `PATCH /controls/conversations/{conversation_id}`，支持人工接管、暂停会话、白名单、黑名单的页面切换。
- P5-6 客户身份页：customers、identity drafts/candidates、自我身份全局编辑。
  - 已完成第一版：`/customers` 页面接入 `GET /customers`、`GET /customers/{customer_id}`，支持客户搜索、客户详情、标签/备注/最近联系展示。
  - 已完成第一版：接入 `GET /identity/drafts` 与 `GET /identity/candidates`，在右侧待确认客户区域展示身份草稿和疑似候选数量。
  - 已完成第一版：接入 `GET/PATCH /identity/self/global`，支持在客户页编辑全局自我身份名称和身份事实；保存失败/成功均有页面反馈。
- P5-7 知识库页：新增 `/knowledge` 页面和 sidebar，接 status/search/import/web-build。
  - 已完成第一版：新增 `/knowledge` 页面和 sidebar 入口，接入 `GET /knowledge/status` 展示索引状态、文档数、片段数、支持格式和最近构建时间。
  - 已完成第一版：接入 `GET /knowledge/search`，支持输入问题检索本地知识库并展示片段、相关度和 chunk id。
  - 已完成第一版：接入 `POST /knowledge/import` 与 `POST /knowledge/web-build`，支持填写/拖入文件路径后触发本地拆分入库和联网扩库，页面展示最近任务结果。
- P5-8 前端联调验收：空态、错误态、后端未启动、微信未运行、`npm run build`。
  - 已完成第一版：新增 `npm run verify:p5`，验收五个一级页面、知识库侧边栏顺序、API 客户端覆盖、后端离线错误态、消息发送确认和知识库入库/扩库入口。
  - 已完成第一版：P5 验收三件套通过：`npm run verify:p5`、`npx tsc --noEmit --pretty false`、`npm run build`。
  - 已完成第一版：本地开发服务五个页面路由均可访问：`/`、`/messages`、`/customers`、`/knowledge`、`/settings`。

#### P6 SSE 实时推送

目标：前端不再高频轮询状态，先做单向事件流。

- P6-1 定义事件 schema：`{id,type,timestamp,data,trace_id}`。
  - 已完成第一版：沿用 P4 冻结的事件外壳，并新增前端 `ServerEventEnvelope` 类型。
- P6-2 实现轻量事件中心和 `GET /api/v1/events` SSE。
  - 已完成第一版：新增内存 `EventBus`、SSE 格式化和 `GET /api/v1/events`；支持 `replay` 历史回放、`once=true` 诊断模式和心跳。
- P6-3 接入 runtime/logs/conversations/controls/knowledge/settings/environment 关键变化。
  - 已完成第一版：runtime start/stop/restart 发布 `runtime.status`；消息发送发布 `message.sent`；会话控制、设置、隐私策略和保留策略发布 `log.event`；知识库导入/联网扩库发布 `knowledge.progress`。
  - 已补完后半段第一版：真实守护循环在 unread/active 两条链路都会写入 `message_received` 运行时日志；服务端通过 `RuntimeEventRelay` 把日志桥接为 `message.received`、`message.sent`、`log.event`、`error`，并把微信窗口探测变化桥接为 `log.event(event_type=window.environment.changed)`。
  - 后续保留项：如需更细粒度的窗口焦点/最小化恢复动作事件，可继续拆出专门的 `window.*` typed events。
- P6-4 前端接 EventSource，替代首页/消息/日志高频轮询。
  - 已完成第一版：新增 `desktop_app/frontend/lib/events.ts` 和 `desktop_app/frontend/hooks/use-server-events.ts`；首页监听 `runtime.status/log.event` 后刷新运行状态，消息页监听 `message.sent/message.received/log.event` 后刷新会话与详情，知识库页监听 `knowledge.progress` 后刷新入库状态。
  - 已补完后半段第一版：layout 级新增全局事件监听器和 toast 通知，能够消费新消息、窗口环境变化、运行时错误和锚点丢失等日志事件。
  - 后续保留项：当前页面仍保留必要的手动刷新作为降级路径，未来可继续补独立日志页/通知中心。
- P6-5 断线重连和事件丢失策略。
  - 已完成第一版：服务端支持 `replay`，前端 hook 默认订阅最近事件并在组件卸载时关闭连接；`EventBus` 已补成真正的增量等待/唤醒模型，SSE 不再只是“初始回放 + 心跳”。
  - 后续保留项：更完整的 Last-Event-ID 续传、跨页面统一事件缓存和异常提示留到下一批。

#### P7 Electron 桌面壳

目标：把后端和前端组装成可后台运行的桌面应用。

- P7-1 后端进程检测/拉起/复用：检测 `127.0.0.1:8765`，必要时启动 uvicorn。
  - 已完成第一版：新增 `desktop_app/electron/backend-controller.cjs`，支持健康探测、复用已运行后端、必要时拉起本地 uvicorn，并区分 `reused` 与 `managed` 会话。
- P7-2 停止策略：关闭窗口不等于停止守护；退出应用才 stop runtime 和后端。
  - 已完成第一版：新增 `desktop_app/electron/lifecycle-controller.cjs`，窗口关闭默认按静默后台策略隐藏；真正退出时先调用 `/api/v1/runtime/stop`，再停止由壳层拉起的 managed backend。
- P7-3 托盘菜单：开始、暂停、停止、显示窗口、打开日志目录、退出。
  - 已完成第一版：新增 `desktop_app/electron/shell-controller.cjs` 与 `main.cjs` 托盘接线；当前已支持显示主窗口、开始守护、暂停守护、停止守护、退出应用五项基础菜单，并根据后端 `tray-state` 动态更新 tooltip 和可用状态。
- P7-4 静默后台与 ESC：接 `run_silently`、`esc_action`。
  - 已完成第一版：壳层启动后会读取 `/api/v1/settings` 中的 `run_silently` 与 `esc_action`；`ESC` 目前支持 `pause / stop / hide / quit` 四类动作，并在 `run_silently=true` 时优先隐藏窗口。
- P7-5 定时启停：壳层定时 tick 调用后端 schedule。
  - 已完成第一版：后端新增 `/api/v1/shell/schedule-status` 与 `/api/v1/shell/schedule/tick`；Electron 壳启动后会读取 schedule 状态，并按本地 shell 偏好中的 `scheduleTickIntervalSeconds` 周期性调用 tick，在不把调度逻辑复制进壳层的前提下复用后端 schedule 判定。设置页高级设置已补充“定时巡检间隔”入口。
- P7-6 开机自启：先做壳层设置，不让 Python 服务自己注册系统启动项。
  - 已完成第一版：新增 `desktop_app/electron/shell-preferences.cjs`，把 `launchAtLogin` 与定时 tick 间隔保存在壳层本地 `shell-preferences.json`；壳层启动时通过 Electron `setLoginItemSettings` 同步开机自启，不让 Python 服务自己写系统启动项。设置页高级设置已补充“开机自启”入口，并在浏览器开发态优雅降级为不可编辑。

#### P8 长跑验收

目标：把桌面客户端冻结成“可长期使用的运营控制台”，先验收身份链路、知识链路、桌面壳可用性，再验收长跑稳定性。

- P8-1 身份提示词链路验收：验证“用户/自我身份编辑 -> prompt evidence -> 模型回答”。
- P8-2 知识库检索链路验收：验证“本地导入/联网扩库 -> retrieval evidence -> 回答上下文”。
- P8-3 桌面壳操作性验收：设置页、开机自启、定时巡检、窗口加载诊断均可用。
- P8-4 30 分钟/2 小时/8 小时长跑稳定性验收：固化 JSON 报告和扰动场景清单。
- P8-5 release checklist 与 runbook：形成发布前门槛和交付文档。

1. 服务层骨架：`wechat_ai/server`、FastAPI、`/api/v1`、ping、health。
2. API 契约：统一响应结构、错误码、`trace_id`。
3. RuntimeManager：单实例、start、stop、status、soft stop。
   当前进度：已完成第一版本地 API 包装，提供 `/api/v1/runtime/status/start/stop`，支持 `global` 模式、重复启动保护和非运行停止保护；`P0-4` 已把 `stop_event` 从 `DesktopAppService` 传入守护 runner，并接入真实 `run_global_auto_reply` 主循环。
4. stop_event：补齐轮询、等待、模型调用前、发送前、重试前检查点。
   当前进度：已覆盖主循环入口、轮询处理后、普通 sleep、异常 backoff sleep，并在停止时记录 `stop_event_received`，退出前复用 shutdown flush 处理 pending 消息。模型调用前/发送前的更细粒度中断留到后续真实 runner 收口时继续拆。
5. 配置中心：读取来源优先级、前端可见配置来源、敏感字段脱敏。
6. 日志接口：recent logs、错误过滤、`trace_id` 查询。
7. 客户端首批接口：首页、设置、客户、自我身份、知识库。
8. UI 自动化稳定性专项：窗口、登录、焦点、发送前后校验、顺序与去重。
9. 消息页真实闭环：suggest_reply、send_reply、人工接管、会话暂停。
10. 数据保留策略：日志轮转、memory 裁剪、清空入口。
11. SQLite 元数据层。
12. WebSocket 实时推送。
13. Electron 客户端打包。
