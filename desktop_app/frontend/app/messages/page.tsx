"use client"

import type { ReactNode } from "react"
import { useCallback, useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingState, EmptyState } from "@/components/api-state"
import { useServerEvents } from "@/hooks/use-server-events"
import { UserAvatar } from "@/components/user-avatar"
import { apiClient } from "@/lib/api"
import type { ConversationControlPatch, ConversationDetail, ConversationListItem, ReplySuggestion } from "@/lib/api"
import {
  ImageIcon,
  MessageSquareText,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Send,
  ShieldAlert,
  Smile,
  Sparkles,
  UserRoundCheck,
} from "lucide-react"

export default function MessagesPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [query, setQuery] = useState("")
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState("")
  const [draft, setDraft] = useState("")
  const [suggestion, setSuggestion] = useState<ReplySuggestion | null>(null)
  const [actionMessage, setActionMessage] = useState("")
  const [actionError, setActionError] = useState("")
  const [busyAction, setBusyAction] = useState<"suggest" | "send" | "control" | "">("")

  const loadConversations = useCallback(async () => {
    setError("")
    const response = await apiClient.listConversations()
    if (!response.success || !response.data) {
      setError(response.error ? `${response.error.code}: ${response.error.message}` : "会话列表加载失败")
      setLoadingList(false)
      return
    }
    const list = response.data
    setConversations(list)
    setSelectedId((current) => current || list[0]?.conversation_id || "")
    setLoadingList(false)
  }, [])

  const loadConversation = useCallback(async (conversationId: string) => {
    if (!conversationId) return
    setLoadingDetail(true)
    setError("")
    const response = await apiClient.getConversation(conversationId)
    if (!response.success || !response.data) {
      setError(response.error ? `${response.error.code}: ${response.error.message}` : "会话详情加载失败")
      setLoadingDetail(false)
      return
    }
    setDetail(response.data)
    setSuggestion(null)
    setDraft("")
    setLoadingDetail(false)
  }, [])

  useEffect(() => {
    void loadConversations().catch((err: unknown) => {
      setLoadingList(false)
      setError(err instanceof Error ? err.message : "无法连接本地后端服务")
    })
  }, [loadConversations])

  useEffect(() => {
    void loadConversation(selectedId).catch((err: unknown) => {
      setLoadingDetail(false)
      setError(err instanceof Error ? err.message : "无法读取会话详情")
    })
  }, [loadConversation, selectedId])

  useServerEvents((event) => {
    if (event.type === "message.sent" || event.type === "message.received") {
      void loadConversations()
      if (selectedId) void loadConversation(selectedId)
      return
    }
    if (event.type === "log.event") {
      const eventType = String(event.data.event_type ?? "")
      if (eventType === "conversation.control.updated" && selectedId) {
        void loadConversation(selectedId)
      }
    }
  }, { eventTypes: ["message.sent", "message.received", "log.event"], replay: 1 })

  const filtered = conversations.filter((item) => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return true
    return `${item.title} ${item.latest_message}`.toLowerCase().includes(keyword)
  })
  const latestIncoming = [...(detail?.messages ?? [])].reverse().find((item) => item.direction !== "outgoing")

  async function handleSuggestReply() {
    if (!detail) return
    setActionError("")
    setActionMessage("")
    setBusyAction("suggest")
    const messageText = latestIncoming?.text || detail.conversation.latest_message || ""
    try {
      const response = await apiClient.suggestReply(detail.conversation.conversation_id, messageText)
      if (!response.success || !response.data) {
        setActionError(response.error ? `${response.error.code}: ${response.error.message}` : "建议回复生成失败")
        return
      }
      setSuggestion(response.data)
      setDraft(response.data.suggestion)
      setActionMessage(response.data.status === "ready" ? "建议回复已写入草稿" : `建议回复状态：${response.data.status}`)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "无法连接建议回复接口")
    } finally {
      setBusyAction("")
    }
  }

  async function handleSendReply() {
    if (!detail) return
    const text = draft.trim()
    if (!text) {
      setActionError("发送内容不能为空")
      return
    }
    if (!window.confirm("确认要把当前草稿发送到微信会话吗？")) return
    setActionError("")
    setActionMessage("")
    setBusyAction("send")
    try {
      const response = await apiClient.sendConversationReply(detail.conversation.conversation_id, text)
      if (!response.success || !response.data) {
        setActionError(response.error ? `${response.error.code}: ${response.error.message}` : "发送失败")
        return
      }
      if (response.data.status === "sent") {
        setActionMessage("发送成功，已刷新会话")
        setDraft("")
        await loadConversation(detail.conversation.conversation_id)
        void loadConversations()
        return
      }
      setActionError(`${response.data.status || "blocked"}：${response.data.reason || response.data.reason_code || "发送未完成"}`)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "无法连接发送接口")
    } finally {
      setBusyAction("")
    }
  }

  async function handleControlPatch(patchBody: ConversationControlPatch) {
    if (!detail) return
    setActionError("")
    setActionMessage("")
    setBusyAction("control")
    try {
      const response = await apiClient.updateConversationControl(detail.conversation.conversation_id, patchBody)
      if (!response.success || !response.data) {
        setActionError(response.error ? `${response.error.code}: ${response.error.message}` : "会话控制更新失败")
        return
      }
      setDetail((current) => current ? { ...current, control: response.data! } : current)
      setActionMessage("会话控制已更新")
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "无法更新会话控制")
    } finally {
      setBusyAction("")
    }
  }

  return (
    <AppShell title="消息">
      <div className="flex min-h-[656px] flex-1">
        <aside className="w-[280px] shrink-0 border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="mb-3 text-[15px] font-semibold text-slate-800">会话列表</h2>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索客户或内容"
                className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>
          {loadingList ? (
            <div className="p-4">
              <LoadingState label="正在加载会话" />
            </div>
          ) : filtered.length ? (
            <ul>
              {filtered.map((item) => (
                <ConversationRow
                  key={item.conversation_id}
                  item={item}
                  active={item.conversation_id === selectedId}
                  onClick={() => setSelectedId(item.conversation_id)}
                />
              ))}
            </ul>
          ) : (
            <div className="p-4">
              <EmptyState title="暂无会话" />
            </div>
          )}
        </aside>

        <section className="flex flex-1 flex-col bg-[#f6f7f9]">
          {error ? <div className="p-4"><ErrorState message={error} /></div> : null}
          {loadingDetail ? (
            <div className="p-6">
              <LoadingState label="正在加载会话详情" />
            </div>
          ) : detail ? (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-[15px] font-semibold text-slate-800">{detail.conversation.title}</span>
                  <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">
                    {detail.conversation.is_group ? "群聊" : "微信"}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-slate-400">
                  <span className="text-xs tabular-nums">{formatTime(detail.conversation.updated_at)}</span>
                  <MoreHorizontal className="h-4 w-4" />
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
                {detail.messages.length ? (
                  detail.messages.map((message) =>
                    message.direction === "outgoing" ? (
                      <OutgoingBubble key={message.message_id} time={formatTime(message.sent_at)}>
                        {message.text}
                      </OutgoingBubble>
                    ) : (
                      <IncomingBubble key={message.message_id} name={message.sender || detail.conversation.title} time={formatTime(message.sent_at)}>
                        {message.text}
                      </IncomingBubble>
                    ),
                  )
                ) : (
                  <EmptyState title="暂无消息记录" />
                )}
              </div>

              <div className="border-t border-slate-200 bg-white px-6 py-3">
                <div className="mb-2 flex items-center gap-3 text-slate-400">
                  <Smile className="h-4 w-4" />
                  <ImageIcon className="h-4 w-4" />
                  <Paperclip className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-3">
                  <input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="输入或编辑 AI 建议回复，发送前会再次确认"
                    className="h-9 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
                  />
                  <button
                    disabled={busyAction === "send"}
                    onClick={handleSendReply}
                    className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-500 px-4 text-sm font-medium text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    <Send className="h-4 w-4" />
                    {busyAction === "send" ? "发送中" : "发送"}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-6">
              <EmptyState title="请选择一个会话" />
            </div>
          )}
        </section>

        <aside className="w-[280px] shrink-0 border-l border-slate-200 bg-white p-5">
          {actionMessage ? <div className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">{actionMessage}</div> : null}
          {actionError ? <div className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">{actionError}</div> : null}
          <AssistantPanel
            detail={detail}
            suggestion={suggestion}
            busy={busyAction === "suggest"}
            onSuggest={handleSuggestReply}
            onApply={() => suggestion?.suggestion ? setDraft(suggestion.suggestion) : undefined}
          />
          <ControlPanel detail={detail} busy={busyAction === "control"} onPatch={handleControlPatch} />
        </aside>
      </div>
    </AppShell>
  )
}

function ConversationRow({
  item,
  active,
  onClick,
}: {
  item: ConversationListItem
  active: boolean
  onClick: () => void
}) {
  return (
    <li
      onClick={onClick}
      className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-5 py-3.5 ${
        active ? "bg-blue-50/70" : "hover:bg-slate-50"
      }`}
    >
      <UserAvatar name={item.title} size={40} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-slate-800">{item.title}</span>
          <span className="shrink-0 text-xs text-slate-400 tabular-nums">{formatTime(item.updated_at)}</span>
        </div>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="truncate text-xs text-slate-500">{item.latest_message}</span>
          {item.unread_count ? (
            <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-medium text-white">
              {item.unread_count}
            </span>
          ) : null}
        </div>
      </div>
    </li>
  )
}

function AssistantPanel({
  detail,
  suggestion,
  busy,
  onSuggest,
  onApply,
}: {
  detail: ConversationDetail | null
  suggestion: ReplySuggestion | null
  busy: boolean
  onSuggest: () => void
  onApply: () => void
}) {
  const latestIncoming = [...(detail?.messages ?? [])].reverse().find((item) => item.direction !== "outgoing")
  return (
    <div className="mb-6 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
      <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-blue-600">
        <Sparkles className="h-4 w-4" />
        AI 建议回复
      </div>
      <p className="mb-4 text-xs leading-relaxed text-slate-600">
        {suggestion?.suggestion || (latestIncoming ? `基于最近消息：“${latestIncoming.text}”` : "选择会话后可生成建议回复。")}
      </p>
      <div className="space-y-2">
        <button
          disabled={!detail || !suggestion?.suggestion}
          onClick={onApply}
          className="w-full rounded-lg bg-blue-500 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          写入草稿
        </button>
        <button
          disabled={!detail || busy}
          onClick={onSuggest}
          className="w-full rounded-lg border border-slate-200 bg-white py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
        >
          {busy ? "生成中" : suggestion ? "重新生成" : "生成建议"}
        </button>
        <button disabled className="flex w-full cursor-not-allowed items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white py-2 text-sm text-slate-400">
          <MessageSquareText className="h-4 w-4" />
          人工接管见下方控制
        </button>
      </div>
    </div>
  )
}

function ControlPanel({
  detail,
  busy,
  onPatch,
}: {
  detail: ConversationDetail | null
  busy: boolean
  onPatch: (patchBody: ConversationControlPatch) => void
}) {
  const control = detail?.control
  return (
    <div>
      <div className="mb-3 text-sm font-medium text-slate-800">客户信息</div>
      <dl className="space-y-3 text-xs">
        <InfoRow label="标签">
          <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-600">{detail?.conversation.is_group ? "群聊" : "个人客户"}</span>
          <button className="flex h-4 w-4 items-center justify-center rounded-full border border-dashed border-slate-300 text-slate-400">
            <Plus className="h-3 w-3" />
          </button>
        </InfoRow>
        <InfoRow label="状态">
          <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-600">{control?.paused ? "已暂停" : "跟进中"}</span>
        </InfoRow>
        <InfoRow label="人工接管">
          <ControlBadge active={Boolean(control?.human_takeover)} />
        </InfoRow>
        <InfoRow label="会话暂停">
          <ControlBadge active={Boolean(control?.paused)} />
        </InfoRow>
        <InfoRow label="黑名单">
          <ControlBadge active={Boolean(control?.blacklisted)} danger />
        </InfoRow>
        <InfoRow label="最近联系">
          <span className="text-slate-600 tabular-nums">{formatDate(detail?.conversation.updated_at)}</span>
        </InfoRow>
      </dl>
      <div className="mt-5 grid grid-cols-2 gap-2">
        <ControlButton
          disabled={!detail || busy}
          active={Boolean(control?.human_takeover)}
          onClick={() => onPatch({ human_takeover: !control?.human_takeover })}
        >
          {control?.human_takeover ? "取消接管" : "人工接管"}
        </ControlButton>
        <ControlButton
          disabled={!detail || busy}
          active={Boolean(control?.paused)}
          onClick={() => onPatch({ paused: !control?.paused })}
        >
          {control?.paused ? "恢复会话" : "暂停会话"}
        </ControlButton>
        <ControlButton
          disabled={!detail || busy}
          active={Boolean(control?.whitelisted)}
          onClick={() => onPatch({ whitelisted: !control?.whitelisted })}
        >
          {control?.whitelisted ? "移出白名单" : "加入白名单"}
        </ControlButton>
        <ControlButton
          disabled={!detail || busy}
          active={Boolean(control?.blacklisted)}
          danger
          onClick={() => onPatch({ blacklisted: !control?.blacklisted })}
        >
          {control?.blacklisted ? "移出黑名单" : "加入黑名单"}
        </ControlButton>
      </div>
    </div>
  )
}

function ControlButton({
  active,
  danger,
  disabled,
  onClick,
  children,
}: {
  active: boolean
  danger?: boolean
  disabled?: boolean
  onClick: () => void
  children: ReactNode
}) {
  const activeClass = danger ? "border-rose-200 bg-rose-50 text-rose-600" : "border-blue-200 bg-blue-50 text-blue-600"
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg border px-2 py-2 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-50 ${
        active ? activeClass : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  )
}

function ControlBadge({ active, danger }: { active: boolean; danger?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 ${active ? (danger ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600") : "bg-slate-50 text-slate-500"}`}>
      {danger ? <ShieldAlert className="h-3 w-3" /> : <UserRoundCheck className="h-3 w-3" />}
      {active ? "是" : "否"}
    </span>
  )
}

function IncomingBubble({ name, time, children }: { name: string; time?: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <UserAvatar name={name} size={32} />
      <div>
        <div className="max-w-[430px] rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm">{children}</div>
        {time ? <div className="mt-1 text-xs text-slate-400">{time}</div> : null}
      </div>
    </div>
  )
}

function OutgoingBubble({ time, children }: { time?: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-end gap-2">
      <div className="max-w-[430px]">
        <div className="mb-1 flex items-center justify-end gap-1.5 text-xs text-slate-400">
          <Sparkles className="h-3 w-3" />
          <span>自动回复</span>
          {time ? <span className="tabular-nums">{time}</span> : null}
        </div>
        <div className="rounded-2xl rounded-tr-sm bg-[#95ec69] px-4 py-2.5 text-sm text-slate-800">{children}</div>
      </div>
    </div>
  )
}

function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500">{label}</dt>
      <dd className="flex items-center gap-1.5">{children}</dd>
    </div>
  )
}

function formatTime(value: string | null | undefined) {
  if (!value) return "--:--"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value.slice(11, 16) || "--:--"
  return parsed.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
}

function formatDate(value: string | null | undefined) {
  if (!value) return "--"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}
