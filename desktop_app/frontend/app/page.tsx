"use client"

import type { ReactNode } from "react"
import { useCallback, useEffect, useState, useTransition } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingState } from "@/components/api-state"
import { useServerEvents } from "@/hooks/use-server-events"
import { apiClient } from "@/lib/api"
import type { DashboardSummary, LogsSummary, RecentLogEvent, RuntimeAction, RuntimeStatus, WechatEnvironment } from "@/lib/api"
import {
  Bell,
  Bot,
  CheckCircle2,
  ChevronRight,
  ListTodo,
  MessageCircle,
  Play,
  RefreshCw,
  Settings,
  Square,
  UserPlus,
  Users,
} from "lucide-react"

type HomeState = {
  dashboard: DashboardSummary | null
  runtime: RuntimeStatus | null
  logsSummary: LogsSummary | null
  environment: WechatEnvironment | null
  recentLogs: RecentLogEvent[]
}

const emptyState: HomeState = {
  dashboard: null,
  runtime: null,
  logsSummary: null,
  environment: null,
  recentLogs: [],
}

export default function HomePage() {
  const router = useRouter()
  const [state, setState] = useState<HomeState>(emptyState)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [isPending, startTransition] = useTransition()
  const [currentTime, setCurrentTime] = useState("--:--:--")
  const [bootstrapHint, setBootstrapHint] = useState("")
  const [environmentChecked, setEnvironmentChecked] = useState(false)

  const loadHomeData = useCallback(async () => {
    setError("")
    const [dashboard, runtime, logsSummary, recentLogs] = await Promise.all([
      apiClient.getDashboardSummary(),
      apiClient.getRuntimeStatus(),
      apiClient.getLogsSummary(20),
      apiClient.getRecentLogs(3),
    ])

    const failed = [dashboard, runtime, logsSummary, recentLogs].find((item) => !item.success)
    if (failed?.error) {
      setError(`${failed.error.code}: ${failed.error.message}`)
    }

    setState((previous) => ({
      dashboard: dashboard.data,
      runtime: runtime.data,
      logsSummary: logsSummary.data,
      environment: previous.environment,
      recentLogs: recentLogs.data ?? [],
    }))
    setLoading(false)
  }, [])

  useEffect(() => {
    void loadHomeData().catch((err: unknown) => {
      setLoading(false)
      setError(err instanceof Error ? err.message : "无法连接本地后端服务")
    })
  }, [])

  useEffect(() => {
    setCurrentTime(formatClock(new Date()))
    const timer = window.setInterval(() => {
      setCurrentTime(formatClock(new Date()))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  useServerEvents(() => {
    void loadHomeData()
  }, { eventTypes: ["runtime.status", "log.event"], replay: 1 })

  function runAction(action: "check" | "start" | "stop") {
    startTransition(async () => {
      setError("")
      setBootstrapHint("")
      if (action === "check") {
        setEnvironmentChecked(false)
        const result = await apiClient.bootstrapCheckRuntime()
        if (!result.success) {
          setError(result.error ? `${result.error.code}: ${result.error.message}` : "微信环境检测失败")
          const detailMessage = formatBootstrapError(result.error?.detail)
          if (result.error && detailMessage) {
            setError(`${result.error.code}: ${detailMessage}`)
          }
          return
        }
        if (result.data) {
          const bootstrapReady = Boolean(result.data.bootstrap?.ui_ready)
          const environment = result.data.bootstrap?.environment as WechatEnvironment | undefined
          if (environment) {
            setState((previous) => ({ ...previous, environment }))
          }
          setEnvironmentChecked(bootstrapReady)
          setBootstrapHint(
            bootstrapReady
              ? formatBootstrapHint(result.data) || "微信主界面已识别。确认无误后，可以点击“确认开始自动回复”。"
              : formatBootstrapHint(result.data) || "已检测到微信进程，但还没有识别到微信主界面。请扫码登录并保持微信窗口可见后再次检测。",
          )
        }
        await loadHomeData()
        return
      }
      if (action === "start") {
        if (!environmentChecked) {
          setError("请先检测微信环境，确认窗口和停止入口可用后再开始自动回复。")
          return
        }
        if (!window.confirm("确认开始自动回复后，程序会开始轮询微信消息，并可能短暂接管微信窗口。确认继续吗？")) {
          return
        }
      }
      const result = action === "start" ? await apiClient.bootstrapStartRuntime() : await apiClient.forceStopRuntime()
      if (!result.success) {
        if (action === "start") {
          setEnvironmentChecked(false)
        }
        setError(result.error ? `${result.error.code}: ${result.error.message}` : "操作失败")
        const detailMessage = formatBootstrapError(result.error?.detail)
        if (result.error && detailMessage) {
          setError(`${result.error.code}: ${detailMessage}`)
          return
        }
        return
      }
      if (result.data) {
        const runtimeAction = result.data
        setState((previous) => ({
          ...previous,
          runtime: runtimeAction,
          dashboard: previous.dashboard
            ? {
                ...previous.dashboard,
                app: {
                  ...previous.dashboard.app,
                  daemon_state: runtimeAction.state,
                },
              }
            : previous.dashboard,
        }))
      }
      if (action === "start") {
        setBootstrapHint("自动回复已启动。需要停止时，请优先使用页面停止按钮；紧急情况下按 Ctrl+Shift+F12。")
      }
      if (action === "stop") {
        const hint = formatBootstrapHint(result.data)
        if (hint) {
          setBootstrapHint(hint)
        }
      }
      await loadHomeData()
    })
  }

  const dashboard = state.dashboard
  const runtime = state.runtime ?? dashboard?.runtime
  const app = dashboard?.app
  const environment = state.environment
  const synced = Boolean(runtime?.running)

  return (
    <AppShell
      title="首页"
      headerRight={
        <div className="flex items-center gap-4 text-sm">
          <div className={`flex items-center gap-2 font-medium ${synced ? "text-emerald-600" : "text-slate-500"}`}>
            <span className={`h-2 w-2 rounded-full ${synced ? "bg-emerald-500" : "bg-slate-300"}`} />
            <span>{synced ? "同步正常" : "等待同步"}</span>
          </div>
          <span className="font-medium text-[var(--app-muted-text)] tabular-nums">{currentTime}</span>
        </div>
      }
    >
      <div className="space-y-5 p-7">
        {error ? <ErrorState message={error} /> : null}
        {!error && bootstrapHint ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            {bootstrapHint}
          </div>
        ) : null}
        {loading ? (
          <LoadingState label="正在连接本地后端服务" />
        ) : (
          <>
            <div className="grid grid-cols-5 gap-4">
              <StatusCard
                label="微信连接状态"
                icon={<CheckCircle2 className="h-6 w-6 text-emerald-500" />}
                value={environment?.wechat_running ? "已连接" : "未确认"}
                sub={
                  environment?.ui_ready === true
                    ? "微信界面已就绪"
                    : environment?.wechat_running
                      ? "微信进程已识别"
                      : "等待窗口检测"
                }
                valueClass={environment?.wechat_running ? "text-emerald-600" : "text-slate-600"}
              />
              <StatusCard
                label="自动回复状态"
                icon={<Play className="h-6 w-6 fill-blue-500 text-blue-500" />}
                value={runtime?.running ? "运行中" : "已暂停"}
                sub={app?.auto_reply_enabled ? "自动回复已开启" : "自动回复未开启"}
                valueClass={runtime?.running ? "text-blue-600" : "text-slate-600"}
              />
              <StatusCard
                label="今日接待"
                icon={<Users className="h-6 w-6 text-orange-500" />}
                value={String(app?.today_received ?? runtime?.daemon.today_received ?? 0)}
                sub="来自运行统计"
                valueClass="text-[var(--app-strong-text)]"
                accentClass="text-orange-500"
                isNumber
              />
              <StatusCard
                label="今日回复"
                icon={<MessageCircle className="h-6 w-6 text-violet-500" />}
                value={String(app?.today_replied ?? runtime?.daemon.today_replied ?? 0)}
                sub="自动回复成功数"
                valueClass="text-[var(--app-strong-text)]"
                accentClass="text-violet-500"
                isNumber
              />
              <StatusCard
                label="待处理事项"
                icon={<Bell className="h-6 w-6 text-rose-500" />}
                value={String(app?.pending_count ?? (dashboard?.pending.identity_candidates ?? 0))}
                sub={`${state.logsSummary?.recent_error_count ?? 0} 条近期异常`}
                valueClass="text-[var(--app-strong-text)]"
                accentClass="text-rose-500"
                isNumber
              />
            </div>

            <section className="rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] p-5 shadow-[var(--app-card-shadow)]">
              <h2 className="mb-3 text-[17px] font-bold text-[var(--app-title)]">快捷操作</h2>
              <div className="grid grid-cols-4 gap-5">
                <QuickAction
                  icon={<RefreshCw className={`h-5 w-5 text-white ${isPending ? "animate-spin" : ""}`} />}
                  iconBg={environmentChecked ? "bg-emerald-500" : "bg-orange-500"}
                  label={environmentChecked ? "微信环境已检测" : "检测微信环境"}
                  disabled={isPending || Boolean(runtime?.running)}
                  onClick={() => runAction("check")}
                />
                <QuickAction
                  icon={runtime?.running ? <Square className="h-5 w-5 fill-white text-white" /> : <Play className="h-5 w-5 fill-white text-white" />}
                  iconBg={runtime?.running ? "bg-slate-600" : "bg-emerald-500"}
                  label={runtime?.running ? "停止自动回复" : "确认开始自动回复"}
                  disabled={isPending || (!runtime?.running && !environmentChecked)}
                  onClick={() => runAction(runtime?.running ? "stop" : "start")}
                />
                <QuickAction
                  icon={<RefreshCw className={`h-5 w-5 text-white ${isPending ? "animate-spin" : ""}`} />}
                  iconBg="bg-orange-500"
                  label="刷新运行状态"
                  disabled={isPending}
                  onClick={() => void loadHomeData()}
                />
                <QuickAction
                  icon={<Settings className="h-5 w-5 text-white" />}
                  iconBg="bg-blue-500"
                  label="进入设置"
                  onClick={() => router.push("/settings")}
                />
              </div>
            </section>

            <section className="rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] p-5 shadow-[var(--app-card-shadow)]">
              <h2 className="mb-3 text-[17px] font-bold text-[var(--app-title)]">最近动态</h2>
              <ul className="divide-y divide-[var(--app-row-border)]">
                {activityItems(state.recentLogs).map((item) => (
                  <ActivityItem key={item.key} icon={item.icon} text={item.text} time={item.time} />
                ))}
              </ul>
              <div className="mt-4 flex justify-end">
                <button className="flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700">
                  查看更多
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  )
}

function StatusCard({
  label,
  icon,
  value,
  sub,
  valueClass,
  accentClass,
  isNumber,
}: {
  label: string
  icon: ReactNode
  value: string
  sub: string
  valueClass: string
  accentClass?: string
  isNumber?: boolean
}) {
  return (
    <div className="min-h-[118px] rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] p-4 shadow-[var(--app-card-shadow)]">
      <div className={`mb-4 text-sm font-bold ${accentClass ?? valueClass}`}>{label}</div>
      <div className="flex items-center gap-3">
        {icon}
        <span className={`${valueClass} ${isNumber ? "text-2xl font-semibold leading-none" : "text-lg font-bold"}`}>{value}</span>
      </div>
      <div className="mt-3 text-xs font-medium text-[var(--app-muted-text)]">{sub}</div>
    </div>
  )
}

function QuickAction({
  icon,
  iconBg,
  label,
  disabled,
  onClick,
}: {
  icon: ReactNode
  iconBg: string
  label: string
  disabled?: boolean
  onClick?: () => void
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className="flex h-14 items-center justify-center gap-3 rounded-lg border border-[var(--app-action-border)] bg-[var(--app-action-bg)] px-5 text-left transition-colors hover:border-blue-300 hover:bg-[var(--app-action-hover-bg)] disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span className={`flex h-8 w-8 items-center justify-center rounded-full ${iconBg}`}>{icon}</span>
      <span className="text-sm font-bold text-[var(--app-strong-text)]">{label}</span>
    </button>
  )
}

function ActivityItem({ icon, text, time }: { icon: ReactNode; text: string; time: string }) {
  return (
    <li className="flex items-center gap-3 py-3 text-sm">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--app-icon-soft-bg)]">{icon}</span>
      <span className="flex-1 font-semibold text-[var(--app-text)]">{text}</span>
      <span className="text-xs font-semibold text-[var(--app-muted-text)] tabular-nums">{time}</span>
      <ChevronRight className="h-4 w-4 text-[var(--app-chevron)]" />
    </li>
  )
}

function activityItems(logs: RecentLogEvent[]) {
  if (!logs.length) {
    return [
      {
        key: "empty",
        icon: <ListTodo className="h-4 w-4 text-slate-500" />,
        text: "暂无新的运行动态",
        time: "--:--",
      },
    ]
  }
  if (!logs.length) {
    return [
      {
        key: "empty",
        icon: <ListTodo className="h-4 w-4 text-slate-500" />,
        text: "暂无新的运行日志",
        time: "--:--",
      },
    ]
  }
  return logs.slice(0, 3).map((log, index) => {
    const eventType = String(log.event_type ?? "log.event")
    const displayText = formatActivityText(eventType, log)
    return {
      key: `${String(log.timestamp ?? "no-time")}-${eventType}-${index}`,
      icon: eventType.includes("sent") ? (
        <Bot className="h-4 w-4 text-blue-500" />
      ) : eventType.includes("error") || log.reason_code ? (
        <Bell className="h-4 w-4 text-rose-500" />
      ) : (
        <UserPlus className="h-4 w-4 text-emerald-500" />
      ),
      text: displayText,
      time: formatLogTime(log.timestamp),
    }
  })
}

const activityTypeLabels: Record<string, string> = {
  active_anchor_missed: "会话锚点已自动修正",
  bootstrap_completed: "微信环境检测完成",
  bootstrap_started: "开始检测微信环境",
  conversation_memory_written: "聊天记录已保存",
  force_stop_requested: "已触发强制停止",
  heartbeat: "守护进程心跳正常",
  identity_resolved: "用户身份已识别",
  log_event: "运行事件已记录",
  loop_error: "轮询出现异常",
  memory_written: "记忆已写入",
  message_received: "收到新消息",
  message_send_unconfirmed: "消息发送结果待确认",
  message_sent: "自动回复已发送",
  model_completed: "AI 回复已生成",
  prompt_built: "回复提示词已生成",
  retrieval_completed: "知识库检索完成",
  runtime_status: "运行状态已更新",
  send_reply: "正在发送自动回复",
  window_environment_changed: "微信窗口状态变化",
}

function formatActivityText(eventType: string, log: RecentLogEvent) {
  const normalizedType = eventType.replaceAll(".", "_")
  const rawMessage = typeof log.message === "string" ? log.message.trim() : ""
  const exceptionMessage = typeof log.exception_message === "string" ? log.exception_message.trim() : ""
  const normalizedMessage = rawMessage.replaceAll(".", "_")
  const friendlyType = activityTypeLabels[normalizedType] ?? activityTypeLabels[normalizedMessage]

  if (friendlyType) {
    const messageIsInternalCode = rawMessage === eventType || activityTypeLabels[normalizedMessage] || rawMessage.includes("_")
    return rawMessage && !messageIsInternalCode ? `${friendlyType}：${rawMessage}` : friendlyType
  }
  if (rawMessage && !rawMessage.includes("_")) return rawMessage
  if (exceptionMessage) return `运行异常：${exceptionMessage}`
  return normalizedType.replaceAll("_", " ")
}

function formatClock(value: Date) {
  return value.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })
}

function formatLogTime(value: unknown) {
  if (typeof value !== "string" || !value) return "--:--"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value.slice(11, 16) || "--:--"
  return parsed.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
}

function formatBootstrapError(detail: unknown) {
  if (!detail || typeof detail !== "object") return ""
  const payload = detail as { status_lines?: unknown; message?: unknown }
  const statusLines = Array.isArray(payload.status_lines)
    ? payload.status_lines.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : []
  if (statusLines.length) {
    return statusLines[statusLines.length - 1]
  }
  return typeof payload.message === "string" ? payload.message : ""
}

function formatBootstrapHint(runtimeAction: RuntimeAction | null) {
  const bootstrap = runtimeAction?.bootstrap
  if (!bootstrap) return ""
  const lines = bootstrap.status_lines.filter((item) => item.trim().length > 0)
  const summary = lines.slice(-2).join(" / ")
  return summary || bootstrap.message
}
