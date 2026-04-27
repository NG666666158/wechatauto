# pywechat

这是一个面向 Windows 微信桌面端的 AI 自动回复项目。当前仓库的重点已经不只是“能回消息”，而是逐步收口成一套可长期使用的本地运营控制台：

- 运行时负责真实微信消息读取、识别、生成回复与发送确认。
- 桌面客户端负责身份编辑、知识库管理、设置、观测、日志与调度控制。

## 项目定位

当前最准确的描述是：

`一个后端主链路已基本成型、正在向桌面客户端产品化收口的 WeChat AI Runtime。`

需要特别说明的是：

- 微信真实自动化在运行时仍会抢占鼠标和键盘输入。
- 桌面客户端的职责不是替代底层自动化，而是做配置、运营、观测和验收面板。

### 桌面客户端职责

- 编辑用户画像、候选身份、自我身份
- 查看 prompt evidence / retrieval evidence
- 管理本地知识库与联网扩库
- 查看运行状态、日志、异常与统计
- 管理工作时段、托盘、静默后台、开机自启、定时巡检

### 运行时职责

- 真实读取微信窗口消息
- 做身份识别、上下文整理、知识检索
- 调用模型生成回复
- 执行真实发送与发送后确认
- 输出结构化日志、心跳、错误与观测事件

## 当前已具备的能力

- 微信单聊自动回复
- 群聊 `@` 场景自动回复
- unread 会话轮询与 active 当前窗口增量监听
- 多条未读消息聚合回复
- 用户身份识别、候选合并、自我身份分层覆盖
- 本地 memory store
- 本地知识库导入、切分、索引、检索
- `txt / md / json / pdf / docx / 图片 OCR` 入库
- 联网扩库第一版
- 结构化日志、脱敏、保留策略
- 守护模式、心跳、异常退避、长期轮询
- FastAPI 本地桌面后端接口
- Electron 壳第一版与设置页桌面偏好接入

## 文档入口

建议按这个顺序看：

1. [README.md](./README.md)
2. [docs/architecture-overview.md](./docs/architecture-overview.md)
3. [docs/desktop-app-backend.md](./docs/desktop-app-backend.md)
4. [PROJECT_PLAN.md](./PROJECT_PLAN.md)
5. [REFACTOR_PLAN.md](./REFACTOR_PLAN.md)

P8 验收相关文档：

- [docs/p8-acceptance-checklist.md](./docs/p8-acceptance-checklist.md)
- [docs/p8-runbook.md](./docs/p8-runbook.md)
- [docs/p8-long-run-report-template.md](./docs/p8-long-run-report-template.md)
- [docs/p8-release-checklist.md](./docs/p8-release-checklist.md)

## 仓库结构

- `pywechat/`
  早期桌面自动化模块
- `pyweixin/`
  当前微信桌面 UI 自动化主依赖
- `wechat_ai/`
  AI 运行时、身份、知识库、观测、桌面后端 API
- `desktop_app/`
  前端页面、Electron 壳、桌面集成层
- `scripts/`
  启动、调试、导入、验收、测试脚本
- `docs/`
  主文档、架构说明、验收说明

## 快速开始

### 1. 安装依赖

```powershell
py -3 -m pip install -r requirements.txt
```

### 2. 配置环境变量

至少需要：

- `MINIMAX_API_KEY`

常用可选项：

- `MINIMAX_MODEL`
- `WECHAT_CONTEXT_LIMIT`
- `WECHAT_GROUP_MENTION_NAMES`

### 3. 首次启动真实微信自动回复

推荐先走引导脚本：

```powershell
py -3 scripts\bootstrap_wechat_first_run.py --wechat-path C:\Weixin\Weixin.exe --ready-timeout 420 --poll-interval 2 --narrator-settle-seconds 10
```

这个流程会：

- 启动微信
- 启动讲述人
- 等待 UI 自动化环境接管
- 切入正式监听脚本

### 4. 直接启动正式守护

```powershell
py -3 scripts\run_minimax_global_auto_reply.py --forever --poll-interval 1.0 --debug
```

## 桌面客户端与验收

设置页里的桌面壳偏好当前已经接通：

- `开机自启`
- `定时巡检间隔`

P8 验收入口：

```powershell
py -3 scripts\run_p8_shell_acceptance.py --skip-http --format pretty
py -3 scripts\run_p8_acceptance.py --preset smoke --format pretty
```

如果前端服务已经启动，也可以做设置页实时检查：

```powershell
py -3 scripts\run_p8_shell_acceptance.py --frontend-url http://127.0.0.1:3000/settings --format pretty
```

## 数据目录

运行时默认数据目录位于：

- `wechat_ai/data/users/`
- `wechat_ai/data/agents/`
- `wechat_ai/data/self_identity/`
- `wechat_ai/data/knowledge/`
- `wechat_ai/data/memory/`
- `wechat_ai/data/logs/`
- `wechat_ai/data/app/`

## 测试与回归

核心后端回归：

```powershell
py -3 scripts\test_wechat_ai_unit.py
py -3 scripts\test_wechat_ai_app_service_unit.py
py -3 scripts\test_wechat_ai_server_unit.py
py -3 scripts\test_wechat_ai_api_contract_unit.py
```

前端与桌面壳回归：

```powershell
node desktop_app\frontend\tests\p5-frontend-acceptance.mjs
node desktop_app\electron\tests\p7-shell-unit.mjs
node desktop_app\electron\tests\p7-shell-preferences-bridge-unit.mjs
py -3 scripts\test_p8_shell_acceptance_unit.py
```

## 发布前关注点

如果要进入可长期使用阶段，当前最重要的是：

- 身份提示词链路验收
- 知识库检索链路验收
- Electron 设置页与桌面偏好验收
- 30 分钟 / 2 小时 / 8 小时长跑稳定性
- 发送确认失败、anchor missed、loop error 的持续收口
