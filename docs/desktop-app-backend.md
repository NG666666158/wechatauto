# 桌面客户端后端接口说明

本文档说明当前仓库给桌面客户端预留的本地后端服务层。前端原则上只调用本地 HTTP API 或 `DesktopAppService`，不要直接跨层调用 `wechat_runtime.py`、memory、identity repository 等内部模块。

## 启动方式

本地 FastAPI 服务入口：

```powershell
py -3 -m uvicorn wechat_ai.server.main:app --host 127.0.0.1 --port 8765
```

统一 API 前缀：

```text
/api/v1
```

统一响应结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "trace_id": "..."
}
```

## 核心模块

- [wechat_ai/app/service.py](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/service.py)：桌面客户端服务边界。
- [wechat_ai/server/main.py](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/server/main.py)：FastAPI 应用入口。
- [wechat_ai/server/api/](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/server/api)：HTTP 路由。
- [wechat_ai/server/services/runtime_manager.py](/C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/server/services/runtime_manager.py)：运行态生命周期管理。

## 已可接入接口

基础检查：

- `GET /api/v1/ping`
- `GET /api/v1/health`

首页与运行控制：

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/runtime/status`
- `POST /api/v1/runtime/start`
- `POST /api/v1/runtime/stop`
- `POST /api/v1/runtime/restart`

说明：`runtime/stop` 会向下触发 `stop_event`。真实轮询循环会在轮询边界、普通等待、异常 backoff 等位置响应停止，退出前会 flush pending 消息。

设置页：

- `GET /api/v1/settings`
- `PATCH /api/v1/settings`

客户与身份：

- `GET /api/v1/customers`
- `GET /api/v1/customers/{customer_id}`
- `GET /api/v1/identity/drafts`
- `GET /api/v1/identity/candidates`
- `GET /api/v1/identity/self/global`
- `PATCH /api/v1/identity/self/global`

消息页：

- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`
- `POST /api/v1/conversations/{conversation_id}/suggest`
- `POST /api/v1/conversations/{conversation_id}/send`

说明：消息页第一版会话数据来自本地轻量缓存 `wechat_ai/data/app/conversations.json`。真实微信监听链路后续可以在收到/发送消息时写入该缓存，前端先通过统一接口读取，不直接依赖微信窗口控件。

`send` 接口当前已接入发送前校验，会拦截：

- 空文本
- 人工接管
- 会话暂停
- 黑名单

通过校验后：

- 如果 `settings.real_send_enabled=false` 且没有注入发送器，会返回 `status=not_implemented`，用于安全预览。
- 如果注入了发送器，或设置 `real_send_enabled=true`，会调用 pyweixin 发送适配器，并在成功后写入本地会话缓存。
- 发送失败会返回 `status=failed`、`reason_code=SEND_FAILED`，不会写入出站消息。

知识库：

- `GET /api/v1/knowledge/status`
- `GET /api/v1/knowledge/search?q=...&limit=3`
- `POST /api/v1/knowledge/import`
- `POST /api/v1/knowledge/web-build`

运维、隐私与环境检查：

- `GET /api/v1/logs/recent?limit=20`
- `GET /api/v1/privacy/policy`
- `PATCH /api/v1/privacy/policy`
- `POST /api/v1/privacy/apply-retention`
- `GET /api/v1/environment/wechat`

会话控制：

- `GET /api/v1/controls/conversations/{conversation_id}`
- `PATCH /api/v1/controls/conversations/{conversation_id}`

会话控制当前支持字段：

```json
{
  "human_takeover": true,
  "paused": true,
  "whitelisted": false,
  "blacklisted": true
}
```

## 当前数据策略

设置文件：

- `wechat_ai/data/app/desktop_settings.json`

运行状态：

- `wechat_ai/data/app/daemon_state.json`

运行日志：

- `wechat_ai/data/logs/runtime_events.jsonl`

知识库索引：

- `wechat_ai/data/knowledge/local_knowledge_index.json`

隐私与保留策略第一版包括：

- structured log 默认脱敏。
- recent logs 接口会再次脱敏并限制返回数量。
- runtime logs 支持按天数清理。
- memory 文件按快照数量裁剪，避免长期无限增长。
- API Key、token、password、secret、authorization 等字段不应明文进入日志。

## 仍属于占位的接口

下面方法已经完成发送前校验和发送适配器调用，但还需要继续补发送后视觉确认：

- `send_reply(conversation_id, text)`

后续仍需要补：

- 发送后成功判定。
- WebSocket 或轮询状态刷新。

## 前端接入建议

第一批优先接：

1. 首页：`dashboard/summary`、`runtime/status/start/stop/restart`。
2. 设置页：`settings`、`privacy/policy`、`controls/conversations`。
3. 客户页：`customers`、`identity/drafts`、`identity/candidates`、`identity/self/global`。
4. 知识库页：`knowledge/status`、`knowledge/import`、`knowledge/search`、`knowledge/web-build`。
5. 运维区：`logs/recent`、`environment/wechat`。

消息页建议先做展示骨架，真实发送闭环放到 P2。

消息页当前可先接：

1. 会话列表：`GET /api/v1/conversations`。
2. 会话详情：`GET /api/v1/conversations/{conversation_id}`。
3. AI 建议：`POST /api/v1/conversations/{conversation_id}/suggest`。
4. 发送按钮可调用 `POST /api/v1/conversations/{conversation_id}/send`。开发期建议默认关闭 `real_send_enabled`，真实联调时再打开。

## P2-7 真实微信联调清单

真实微信联调前先运行只读 readiness 脚本：

```powershell
py -3 scripts\check_wechat_real_run_readiness.py --format json
```

该脚本只检查和提示，不会启动微信、关闭微信、杀进程或修改配置；无微信环境下也应安全退出 `0`。第一版自动/占位检查包括：

- 微信进程：检测 `WeChat.exe` / `Weixin.exe` 是否已运行。
- 微信路径：检查常见安装路径，以及 `WECHAT_PATH` / `WEIXIN_PATH`。
- 讲述人状态：提示 `Narrator.exe` 是否残留，避免干扰焦点。
- UI ready 占位：保留窗口、登录态、输入框焦点等后续只读探测入口。
- 显示缩放：记录系统 DPI / 缩放比例，便于定位控件坐标问题。
- 权限与前台窗口：提示人工确认微信可见、未最小化、处于同一桌面会话。

仍需人工或后续脚本验证的真实联调项：

- 未读顺序：多个未读会话按预期顺序处理，日志可追踪。
- 群聊 sender：不同群成员连续发言时 sender 不混淆。
- 发送确认：微信 UI、本地会话缓存、运行日志三者一致，且不重复发送。
- 焦点/最小化恢复：微信切后台或最小化后能明确失败位置或恢复。
- 长跑观察：按 30 分钟冒烟、2 小时稳定性、8 小时长跑三档记录异常。

P2-7 当前完成情况：已新增可执行 readiness 清单脚本和单测；发送后视觉确认、真实 UI ready 探测、WebSocket 状态刷新仍保留为后续 P2 子项。
