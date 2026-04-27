# 微信 Runtime 启动与联调模板

这份模板用于后续重复测试网页端、Electron 客户端和后端 runtime 的真实启动链路。

## 固定启动链路

1. 启动开发服务。
2. 前端或客户端先调用 `POST /api/v1/runtime/bootstrap-check`。
3. 用户确认后再调用 `POST /api/v1/runtime/bootstrap-start`。
4. 运行期间用 `POST /api/v1/runtime/stop` 或 `POST /api/v1/runtime/force-stop` 停止。

不要把用户点击“开始自动回复”直接接到 `POST /api/v1/runtime/start`。`/runtime/start` 只保留为底层兼容入口，真实页面和客户端入口必须走 `bootstrap-start`。

## 开发服务启动

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\dev_start.ps1
```

后端默认端口是 `8765`，前端默认端口是 `3000`。

## 环境检测行为

环境检测按钮负责准备微信环境，不负责启动自动回复轮询：

- 如果微信未运行，尝试拉起 `C:\Weixin\Weixin.exe`。
- 如果微信进程已在运行且已有可识别窗口，不再重复执行 `Weixin.exe`，避免弹出额外登录/账号入口窗口。
- 如果微信进程已在运行但没有任何可识别窗口，说明可能是退出后残留进程或窗口被彻底收起，此时只启动一次 `Weixin.exe` 用于显示登录/主窗口。
- 微信已运行时会先检测现有主界面；如果已经能识别 UI，直接返回成功，不启动讲述人。
- 只有现有主界面识别失败时，才尝试拉起讲述人 `Narrator.exe`。
- 如启动了讲述人，会等待其接管 UI，默认 10 秒。
- 每 1 秒探测一次微信主界面。
- 最长等待 120 秒。
- 一旦识别到微信主界面 ready，会立即返回成功，不会等满 120 秒。
- 如果 120 秒内仍未识别到微信主界面，返回 `WECHAT_WINDOW_NOT_FOUND`，不启动轮询。

当前 ready 判定必须来自明确的 `ui_ready=true` 或 `ready=true`。只检测到微信进程存在，不算环境检测通过；只有 pyweixin 的 `Navigator.open_weixin()` 成功拿到 `mmui::MainWindow`，才视为微信已登录且主界面可用。不再额外要求当前打开某个聊天标题，也不再用个人资料、会话列表或新消息读取结果替代登录 ready 判断。

后端 API 的环境检测不直接在 `uvicorn` 进程里跑 pyweixin，而是调用 `scripts\bootstrap_wechat_first_run.py --no-start-guardian --wait-for-ui-ready` 子进程。这样网页端和 Electron 客户端点击“环境检测”时，和已验证的真实桌面权限路径一致。

## 启动自动回复行为

确认开始自动回复按钮负责启动真实轮询：

- 前端必须先确认环境检测通过。
- 后端会再次做一次严格 UI ready 检测。
- 检测通过后才启动 `scripts/run_minimax_global_auto_reply.py --forever ...`。
- 检测失败时返回错误，不会启动 runtime 子进程。

## 30 秒真实联调模板

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\runtime_web_smoke_1min.ps1 -DurationSeconds 30
```

该脚本会：

- 清理旧 runtime。
- 执行 `bootstrap-check`。
- 执行 `bootstrap-start`。
- 留出指定时间给你发送单聊消息和群聊 `@` 消息。
- 到点自动调用 `runtime/stop`。
- 打印近期 runtime 事件和本地会话记录。

如果微信已经登录但在后台运行，该脚本也应通过：环境检测会先复用现有微信窗口做 UI 识别，不重复启动微信；识别通过后再启动 30 秒轮询。2026-04-26 已按该场景验证通过：`bootstrap-check` 第 1 次检测 ready，`bootstrap-start` 成功启动 runtime，30 秒后 `runtime/stop` 正常停止。

如果需要给首次扫码登录更多时间，可以显式指定：

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\runtime_web_smoke_1min.ps1 -DurationSeconds 30 -ReadyTimeoutSeconds 180
```

## 验收点

- 未登录时：环境检测可以拉起微信和讲述人，但不会启动轮询；扫码登录后应尽快识别并返回成功。
- 已登录时：环境检测应在识别到主界面后快速返回，不应固定等待满 120 秒。
- 启动时：只有检测通过后才进入消息轮询。
- 停止时：`runtime/status` 应返回 `running=false`。
- 消息写入：用户消息写入 `incoming`，机器人回复写入 `outgoing`。
- 群聊写入：群聊 `@` 消息写入 `group:<群名>` 会话。

## 已知风险

- 微信自动化运行时会短暂占用前台窗口、鼠标和键盘，这是底层 pyweixin/pywinauto 的限制。
- 如果后端不是在真实桌面会话里启动，可能无法识别微信 4.1 主窗口。
- 如果 Narrator 启动失败，环境检测可能无法 ready；此时不应继续启动自动回复。
