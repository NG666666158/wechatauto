# pywechat

这是一个基于 Windows 微信桌面端自动化能力构建的 AI 自动回复项目。

当前仓库可以理解为两层结构：

1. `pywechat/`、`pyweixin/`
负责微信窗口识别、消息读取、消息发送等桌面自动化能力。
2. `wechat_ai/`
负责消息编排、用户身份识别、自我身份管理、画像与记忆、知识库检索、日志与守护运行。

当前项目的实际状态是：

- 后端主链路已经成型，可做真实微信自动回复联调。
- 桌面客户端后端接口已经铺好，但前端与桌面壳层仍在组装阶段。
- 文档体系已经按“主文档 / 架构说明 / 计划清单 / 历史归档”重新整理。

## 文档入口

建议按下面顺序阅读：

1. [README.md](/C:/github/pywechat/pywechat-main/pywechat-main/README.md)
2. [docs/architecture-overview.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/architecture-overview.md)
3. [docs/desktop-app-backend.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/desktop-app-backend.md)
4. [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)

历史阶段性设计和拆解过程统一归档到：

- [docs/superpowers/README.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/superpowers/README.md)

## 当前已经具备的能力

- 微信单聊自动回复
- 微信群聊 `@` 场景自动回复
- 全局轮询未读会话并聚合消息
- 多条未读消息合并回复
- 用户身份识别与候选合并
- 分层自我身份
  - 全局身份
  - 关系身份
  - 用户级覆盖身份
- 用户画像与助手画像读写
- 本地 memory store
- 本地 RAG 检索
- 文档导入与索引重建
  - `txt`
  - `md`
  - `json`
  - `pdf`
  - `docx`
  - 图片 OCR
- 结构化运行日志
- 守护模式、心跳、退避重试、首次启动引导
- 桌面客户端后端服务层基础接口

## 仓库结构

- `pywechat/`
  早期桌面自动化模块
- `pyweixin/`
  当前微信桌面 UI 自动化主依赖
- `wechat_ai/`
  AI 运行时与桌面后端接口
- `scripts/`
  启动、调试、导入、测试脚本
- `desktop_app/`
  桌面客户端前端与后续桌面应用集成目录
- `docs/`
  主文档
- `docs/superpowers/`
  历史设计、计划、实现过程归档

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

首次启动推荐走引导脚本：

```powershell
py -3 scripts\bootstrap_wechat_first_run.py --wechat-path C:\Weixin\Weixin.exe --ready-timeout 420 --poll-interval 2 --narrator-settle-seconds 10
```

这个流程会：

- 启动微信
- 启动讲述人
- 等待 UI 自动化环境接管
- 切入正式监听脚本

### 4. 直接启动正式监听

```powershell
py -3 scripts\run_minimax_global_auto_reply.py --forever --poll-interval 1.0 --debug
```

### 5. 其他常用运行方式

单好友自动回复：

```powershell
py -3 scripts\run_minimax_friend_auto_reply.py --friend "Alice" --duration 5min --debug
```

群聊 `@` 自动回复：

```powershell
py -3 scripts\run_minimax_group_at_reply.py --group "Project Group" --duration 5min --debug
```

## 知识库与身份数据

常用脚本：

```powershell
py -3 scripts\ingest_knowledge.py
py -3 scripts\rebuild_index.py
py -3 scripts\show_recent_logs.py --limit 20
py -3 scripts\show_memory_summary.py --chat-id friend_demo
py -3 scripts\show_desktop_app_snapshot.py
```

运行时默认数据目录位于：

- `wechat_ai/data/users/`
- `wechat_ai/data/agents/`
- `wechat_ai/data/self_identity/`
- `wechat_ai/data/knowledge/`
- `wechat_ai/data/memory/`
- `wechat_ai/data/logs/`
- `wechat_ai/data/app/`

## 测试

项目当前以脚本化回归测试为主。

核心后端回归常用命令：

```powershell
py -3 scripts\test_wechat_ai_unit.py
py -3 scripts\test_wechat_ai_reply_pipeline_unit.py
py -3 scripts\test_wechat_ai_identity_integration_unit.py
py -3 scripts\test_wechat_ai_self_identity_integration_unit.py
py -3 scripts\test_wechat_ai_knowledge_importer_unit.py
py -3 scripts\test_pyweixin_smoke.py
py -3 scripts\test_pull_messages_regression.py
```

## 当前项目判断

现在最准确的描述不是“简单脚本”，也还不是“完全成熟的桌面产品”，而是：

`一个后端主链路已基本成型、正在向桌面客户端产品化收口的 WeChat AI Runtime。`

如果你要继续推进客户端开发，请优先看：

- [docs/desktop-app-backend.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/desktop-app-backend.md)
- [PROJECT_PLAN.md](/C:/github/pywechat/pywechat-main/pywechat-main/PROJECT_PLAN.md)
