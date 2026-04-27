# P8 运行手册

## 启动顺序

1. 启动前端开发服务或桌面打包前端。
2. 启动 Electron 壳。
3. 确认本地后端健康检查通过：`GET /api/v1/health`。
4. 依次确认身份页、知识库页、设置页可访问。
5. 进入 30 分钟冒烟观察。
6. 记录日志、截图、长跑报告等产物。
7. 按需恢复运行或执行干净 stop。

## 操作前检查

- 微信已登录且窗口可探测。
- Narrator / UIA 相关前置条件已满足。
- `MINIMAX_API_KEY` 等环境变量已就绪。
- 当前配置中的 `real_send_enabled` 与运行方式一致。

## 验收产物

- `docs/p8-acceptance-checklist.md`
- `docs/p8-long-run-report-template.md`
- `wechat_ai/data/logs/runtime_events.jsonl`
- `wechat_ai/data/logs/long_run_observer.jsonl`

## 退出顺序

1. 先暂停或停止 runtime。
2. 确认没有 pending 消息残留。
3. 关闭 Electron 或隐藏到托盘。
4. 仅在需要时停止本地后端。
