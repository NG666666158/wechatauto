# P8 验收清单

## P8 Acceptance Gate

- 身份信息可以在客户端编辑，并能在 prompt evidence 中看到真实注入结果。
- 知识库导入、检索、联网扩库可以从客户端或 API 触发，并能看到 retrieval evidence。
- Electron 设置页可以稳定打开，并显示桌面壳偏好项。
- `30m / 2h / 8h` 三档长跑都能输出结构化报告。
- 不出现重复发送、卡死 stop、无界日志膨胀。

## 验收分项

### 1. 身份链路

- `GET /api/v1/debug/prompt-preview` 可返回 `resolved_user_id`、`self_identity_profile`、`prompt_preview`。
- `prompt_preview` 中能看到当前自我身份事实。
- 客户状态与身份解析结果一致，不是单独造的一份展示数据。

### 2. 知识链路

- `GET /api/v1/debug/knowledge-acceptance` 可返回 `imported_files`、`search_query`、`retrieved_chunk_ids`。
- 本地导入后可搜索到 chunk，结果与知识页检索一致。
- 联网扩库不会破坏本地索引可用性。

### 3. 桌面壳

- Electron 主窗口能稳定到达 `dom-ready` 或 `did-finish-load`。
- 设置页能看到“开机自启”“定时巡检间隔”。
- preload bridge 在 Electron 模式下可读写壳层偏好。

### 4. 长跑稳定性

- 30 分钟冒烟：验证基本守护和回复不重复。
- 2 小时稳定性：验证恢复、backoff、心跳、事件推送。
- 8 小时长跑：验证日志、memory、窗口状态变化归因。
