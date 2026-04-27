# P6 收尾记录

## 目标

P6 的目标是把桌面前端与本地后端之间的实时事件链路收口到“可验证、可维护、可继续往桌面壳推进”的状态。

本轮收尾重点包括：

- 修复 SSE 建连竞态与阻塞等待问题
- 去掉每个 SSE 客户端重复触发日志扫描和窗口探测的放大效应
- 修复全局通知刷新后重放上一条旧事件的问题
- 跑通前端生产构建
- 固化一份可追溯的验证记录

## 已落地修复

### 1. 后端 SSE 链路

- `wechat_ai/server/services/events.py`
  - `EventBus` 改为异步订阅模型
  - 支持 replay + 增量等待
  - 不再依赖同步 `threading.Condition.wait()`
- `wechat_ai/server/api/events.py`
  - SSE 改为基于订阅流式输出
  - 不再在请求线程里调用 `relay.sync()`
  - 不再存在“回放结束到记录序号之间”的漏事件窗口
- `wechat_ai/server/main.py`
  - `RuntimeEventRelay` 改为服务端后台单点轮询
  - SSE 客户端数量不再放大日志 IO 和窗口探测次数
  - 生命周期切到 FastAPI `lifespan`

### 2. 前端实时通知

- `desktop_app/frontend/components/global-event-listener.tsx`
  - 已见事件 id 写入 `sessionStorage`
  - 页面刷新或热更新后不会重复 toast 最近一条旧事件
- `desktop_app/frontend/hooks/use-server-events.ts`
  - 保留 `enabled` 开关，避免未就绪时过早建连

### 3. Windows 前端构建稳定性

本地 Windows 环境下，Next.js 构建目录曾多次出现 `.next` / `.next-app` 文件锁冲突。

本轮已采用两层规避：

- `desktop_app/frontend/next.config.mjs`
  - `distDir` 支持从 `NEXT_DIST_DIR` 读取
- `desktop_app/frontend/scripts/build-next.ps1`
  - 每次构建使用新的 `.next-build-*` 目录
  - 构建前后自动恢复 `tsconfig.json`
- `desktop_app/frontend/package.json`
  - `dev` 固定走 `next dev --webpack`
  - `build` 固定走 PowerShell 包装脚本

## 本轮已完成验证

以下验证已在当前仓库实际执行通过：

- `py -3 scripts\test_wechat_ai_unit.py`
- `py -3 scripts\test_wechat_ai_server_unit.py`
- `py -3 scripts\test_wechat_ai_api_contract_unit.py`
- `desktop_app/frontend: npx tsc --noEmit --pretty false`
- `desktop_app/frontend: npm run verify:p5`
- `desktop_app/frontend: npm run verify:p6`
- `desktop_app/frontend: npm run build`

其中前端生产构建是在当前桌面环境下以提权方式执行通过，结果为：

- Next.js `16.2.0`
- Webpack 构建模式
- 成功产出静态路由：
  - `/`
  - `/customers`
  - `/knowledge`
  - `/messages`
  - `/settings`

最近一次成功构建输出目录记录在：

- `desktop_app/frontend/build-artifacts/last-build-dir.txt`

## 当前 P6 结论

P6 可以视为完成第一阶段收尾：

- SSE 事件通路已经可用
- 前端已能消费实时事件
- 后端不会因 SSE 客户端数量增加而重复扫描和探测
- 全局通知重复播放问题已锁死
- 前端生产构建已具备稳定绕过本地文件锁的方案

## 进入 P7 前的边界说明

P6 收尾完成后，下一步应直接进入桌面壳层：

- `P7-1` 后端探测 / 拉起 / 复用
- `P7-2` 关闭窗口与真正退出的生命周期策略

P7 不应再重复实现后端业务逻辑，而只做桌面容器层编排。
