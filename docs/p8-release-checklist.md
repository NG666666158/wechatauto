# P8 Release Checklist

## 发布门槛

- 身份提示词证据已验证。
- 知识库检索证据已验证。
- Electron 设置页可见并可编辑“开机自启”“定时巡检间隔”。
- 30 分钟冒烟通过。
- 2 小时稳定性通过。
- 8 小时长跑通过。

## 发布前检查

### 客户端与桌面壳

- `py -3 scripts/run_p8_shell_acceptance.py --frontend-url http://127.0.0.1:3000/settings --format pretty`
- Electron 窗口诊断事件正常输出：
  - `window.did_start_loading`
  - `window.dom_ready`
  - `window.did_finish_load`
  - `window.did_fail_load`

### 身份与知识链路

- `GET /api/v1/debug/prompt-preview` 可看到当前身份事实注入。
- `GET /api/v1/debug/knowledge-acceptance` 可看到 chunk 命中证据。
- 身份页、知识库页、设置页的关键入口均可访问。

### 稳定性

- `py -3 scripts/run_p8_acceptance.py --preset smoke --format pretty`
- 诊断报告中的 `loop_error`、`message_send_unconfirmed`、`active_anchor_missed` 有明确归因。
- 无重复发送、无不可恢复 stop 状态、无失控日志增长。
