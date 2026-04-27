export type ApiErrorPayload = {
  code: string
  message: string
  detail?: unknown
}

export type ApiResponse<T> = {
  success: boolean
  data: T | null
  error: ApiErrorPayload | null
  trace_id: string
}

export type DaemonStatus = {
  state: string
  pid: number | null
  run_silently: boolean
  last_heartbeat: string | null
  last_started_at: string | null
  last_stopped_at: string | null
  last_error: string | null
  consecutive_errors: number
  retry_backoff_seconds: number
  next_retry_at: string | null
  today_received: number
  today_replied: number
}

export type AppStatus = {
  wechat_status: string
  daemon_state: string
  auto_reply_enabled: boolean
  today_received: number
  today_replied: number
  pending_count: number
  knowledge_index_ready: boolean
  last_heartbeat: string | null
}

export type RuntimeStatus = {
  state: string
  mode: string
  running: boolean
  daemon: DaemonStatus
  app: AppStatus
}

export type RuntimeBootstrap = {
  ok: boolean
  wechat_started: boolean
  narrator_started: boolean
  ui_ready: boolean
  guardian_started: boolean
  narrator_stopped: boolean
  attempts: number
  message: string
  guardian_command: string[]
  guardian_exit_code: number | null
  status_lines: string[]
  environment: Record<string, unknown>
}

export type RuntimeAction = RuntimeStatus & {
  bootstrap?: RuntimeBootstrap | null
}

export type KnowledgeStatus = {
  ready: boolean
  index_path: string
  documents_loaded: number
  chunks_created: number
  last_built_at: string | null
  embedding_provider: string | null
  supported_extensions: string[]
}

export type KnowledgeSearchResult = {
  chunk_id: string
  text: string
  score: number
}

export type KnowledgeFileImport = {
  file_name: string
  status: string
}

export type KnowledgeImportResult = {
  files: KnowledgeFileImport[]
  index_rebuilt: boolean
}

export type WebKnowledgeBuildResult = {
  documents: string[]
  search_limit: number
  status: string
}

export type DashboardSummary = {
  app: AppStatus
  runtime: RuntimeStatus
  knowledge: KnowledgeStatus
  pending: {
    identity_drafts: number
    identity_candidates: number
  }
}

export type LogsSummary = {
  recent_count: number
  recent_error_count: number
  last_event_time: string | null
}

export type WechatEnvironment = {
  wechat_running: boolean
  narrator_required: boolean
  ui_ready: boolean | string
}

export type RecentLogEvent = {
  timestamp?: string
  event_type?: string
  trace_id?: string
  message?: string
  reason_code?: string
  [key: string]: unknown
}

export type WorkHours = {
  enabled: boolean
  start: string
  end: string
}

export type PrivacyPolicy = {
  redact_sensitive_logs: boolean
  log_retention_days: number
  memory_retention_days: number
  max_recent_log_events: number
}

export type Settings = {
  auto_reply_enabled: boolean
  reply_style: string
  new_customer_auto_create: boolean
  sensitive_message_review: boolean
  work_hours: WorkHours
  knowledge_chunk_size: number
  knowledge_chunk_overlap: number
  run_silently: boolean
  esc_action: string
  force_stop_hotkey: string
  schedule_enabled: boolean
  schedule_blocks: Array<{
    day_of_week: string
    start: string
    end: string
    label: string
    enabled: boolean
  }>
  privacy: PrivacyPolicy
  human_takeover_sessions: string[]
  paused_sessions: string[]
  whitelist: string[]
  blacklist: string[]
  request_timeout_seconds: number
  retry_attempts: number
  real_send_enabled: boolean
}

export type SettingsPatch = Partial<
  Pick<
    Settings,
    | "auto_reply_enabled"
    | "reply_style"
    | "new_customer_auto_create"
    | "sensitive_message_review"
    | "work_hours"
    | "knowledge_chunk_size"
    | "knowledge_chunk_overlap"
    | "run_silently"
    | "esc_action"
    | "force_stop_hotkey"
    | "schedule_enabled"
    | "schedule_blocks"
    | "privacy"
    | "human_takeover_sessions"
    | "paused_sessions"
    | "whitelist"
    | "blacklist"
    | "request_timeout_seconds"
    | "retry_attempts"
    | "real_send_enabled"
  >
>

export type PrivacyPolicyPatch = Partial<PrivacyPolicy>

export type ConversationListItem = {
  conversation_id: string
  title: string
  is_group: boolean
  latest_message: string
  unread_count: number
  updated_at: string | null
}

export type ConversationMessage = {
  message_id: string
  conversation_id: string
  sender: string
  text: string
  direction: "incoming" | "outgoing" | string
  sent_at: string | null
}

export type ConversationControl = {
  conversation_id: string
  human_takeover: boolean
  paused: boolean
  whitelisted: boolean
  blacklisted: boolean
}

export type ConversationDetail = {
  conversation: ConversationListItem
  messages: ConversationMessage[]
  control: ConversationControl
}

export type ReplySuggestion = {
  conversation_id: string
  input_text: string
  suggestion: string
  status: string
}

export type SendReplyResult = {
  status: string
  allowed: boolean
  conversation_id: string
  text: string
  reason_code: string
  reason: string
}

export type ConversationControlPatch = Partial<Pick<ConversationControl, "human_takeover" | "paused" | "whitelisted" | "blacklisted">>

export type Customer = {
  customer_id: string
  display_name: string
  status: string
  tags: string[]
  remark: string
  last_contact_at: string | null
}

export type IdentityDraft = {
  draft_user_id: string
}

export type IdentityCandidate = {
  candidate_id: string
}

export type SelfIdentity = {
  display_name: string
  identity_facts: string[]
}

export type SelfIdentityPatch = Partial<SelfIdentity>

const API_BASE_URL =
  process.env.NEXT_PUBLIC_WECHAT_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8765/api/v1"

const BOOTSTRAP_READY_TIMEOUT_SECONDS = 120
const BOOTSTRAP_POLL_INTERVAL_SECONDS = 1
const BOOTSTRAP_NARRATOR_SETTLE_SECONDS = 10
const STRICT_BOOTSTRAP_PAYLOAD = {
  mode: "global",
  ready_timeout_seconds: BOOTSTRAP_READY_TIMEOUT_SECONDS,
  poll_interval_seconds: BOOTSTRAP_POLL_INTERVAL_SECONDS,
  narrator_settle_seconds: BOOTSTRAP_NARRATOR_SETTLE_SECONDS,
  wait_for_ui_ready_before_guardian: true,
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  })
  const payload = (await response.json()) as ApiResponse<T>
  if (!response.ok) {
    return {
      success: false,
      data: null,
      error: payload.error ?? {
        code: `HTTP_${response.status}`,
        message: response.statusText || "Request failed",
      },
      trace_id: payload.trace_id ?? response.headers.get("x-trace-id") ?? "",
    }
  }
  return payload
}

function post<T>(path: string, body?: unknown) {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

function patch<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export const apiClient = {
  getDashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
  getRuntimeStatus: () => request<RuntimeStatus>("/runtime/status"),
  getLogsSummary: (limit = 20) => request<LogsSummary>(`/logs/summary?limit=${limit}`),
  getRecentLogs: (limit = 5) => request<RecentLogEvent[]>(`/logs/recent?limit=${limit}`),
  getWechatEnvironment: () => request<WechatEnvironment>("/environment/wechat"),
  startRuntime: () =>
    post<RuntimeAction>("/runtime/bootstrap-start", STRICT_BOOTSTRAP_PAYLOAD),
  bootstrapCheckRuntime: () =>
    post<RuntimeAction>("/runtime/bootstrap-check", STRICT_BOOTSTRAP_PAYLOAD),
  bootstrapStartRuntime: () =>
    post<RuntimeAction>("/runtime/bootstrap-start", STRICT_BOOTSTRAP_PAYLOAD),
  stopRuntime: () => post<RuntimeAction>("/runtime/stop"),
  forceStopRuntime: () => post<RuntimeAction>("/runtime/force-stop"),
  restartRuntime: () =>
    post<RuntimeAction>("/runtime/bootstrap-start", STRICT_BOOTSTRAP_PAYLOAD),
  getSettings: () => request<Settings>("/settings"),
  updateSettings: (patchBody: SettingsPatch) => patch<Settings>("/settings", patchBody),
  getPrivacyPolicy: () => request<PrivacyPolicy>("/privacy/policy"),
  updatePrivacyPolicy: (patchBody: PrivacyPolicyPatch) => patch<PrivacyPolicy>("/privacy/policy", patchBody),
  listConversations: () => request<ConversationListItem[]>("/conversations"),
  getConversation: (conversationId: string) => request<ConversationDetail>(`/conversations/${encodeURIComponent(conversationId)}`),
  suggestReply: (conversationId: string, messageText: string) =>
    post<ReplySuggestion>(`/conversations/${encodeURIComponent(conversationId)}/suggest`, { message_text: messageText }),
  sendConversationReply: (conversationId: string, text: string) =>
    post<SendReplyResult>(`/conversations/${encodeURIComponent(conversationId)}/send`, { text }),
  getConversationControl: (conversationId: string) =>
    request<ConversationControl>(`/controls/conversations/${encodeURIComponent(conversationId)}`),
  updateConversationControl: (conversationId: string, patchBody: ConversationControlPatch) =>
    patch<ConversationControl>(`/controls/conversations/${encodeURIComponent(conversationId)}`, patchBody),
  listCustomers: () => request<Customer[]>("/customers"),
  getCustomer: (customerId: string) => request<Customer>(`/customers/${encodeURIComponent(customerId)}`),
  listIdentityDrafts: () => request<IdentityDraft[]>("/identity/drafts"),
  listIdentityCandidates: () => request<IdentityCandidate[]>("/identity/candidates"),
  getGlobalSelfIdentity: () => request<SelfIdentity>("/identity/self/global"),
  updateGlobalSelfIdentity: (patchBody: SelfIdentityPatch) => patch<SelfIdentity>("/identity/self/global", patchBody),
  getKnowledgeStatus: () => request<KnowledgeStatus>("/knowledge/status"),
  searchKnowledge: (query: string, limit = 3) =>
    request<KnowledgeSearchResult[]>(`/knowledge/search?q=${encodeURIComponent(query)}&limit=${limit}`),
  importKnowledgeFiles: (filePaths: string[]) => post<KnowledgeImportResult>("/knowledge/import", { file_paths: filePaths }),
  buildWebKnowledgeFromDocuments: (filePaths: string[], searchLimit = 5) =>
    post<WebKnowledgeBuildResult>("/knowledge/web-build", { file_paths: filePaths, search_limit: searchLimit }),
}
