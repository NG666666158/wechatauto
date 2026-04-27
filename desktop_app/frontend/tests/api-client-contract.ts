import { apiClient } from "@/lib/api"
import { buildEventsUrl, createEventSource } from "@/lib/events"
import type {
  ApiResponse,
  ConversationControl,
  ConversationControlPatch,
  ConversationDetail,
  ConversationListItem,
  Customer,
  DashboardSummary,
  IdentityCandidate,
  IdentityDraft,
  KnowledgeImportResult,
  KnowledgeSearchResult,
  PrivacyPolicy,
  ReplySuggestion,
  RuntimeAction,
  RuntimeStatus,
  SendReplyResult,
  SelfIdentity,
  SelfIdentityPatch,
  Settings,
  SettingsPatch,
  WebKnowledgeBuildResult,
  WechatEnvironment,
} from "@/lib/api"

async function assertApiClientContract() {
  const dashboard: ApiResponse<DashboardSummary> = await apiClient.getDashboardSummary()
  const runtime: ApiResponse<RuntimeStatus> = await apiClient.getRuntimeStatus()
  const environment: ApiResponse<WechatEnvironment> = await apiClient.getWechatEnvironment()
  const started: ApiResponse<RuntimeAction> = await apiClient.startRuntime()
  const stopped: ApiResponse<RuntimeAction> = await apiClient.stopRuntime()
  const restarted: ApiResponse<RuntimeAction> = await apiClient.restartRuntime()
  const settings: ApiResponse<Settings> = await apiClient.getSettings()
  const updatedSettings: ApiResponse<Settings> = await apiClient.updateSettings({ auto_reply_enabled: false })
  const privacy: ApiResponse<PrivacyPolicy> = await apiClient.getPrivacyPolicy()
  const updatedPrivacy: ApiResponse<PrivacyPolicy> = await apiClient.updatePrivacyPolicy({ log_retention_days: 30 })
  const conversations: ApiResponse<ConversationListItem[]> = await apiClient.listConversations()
  const conversation: ApiResponse<ConversationDetail> = await apiClient.getConversation("friend:zhang")
  const control: ApiResponse<ConversationControl> = await apiClient.getConversationControl("friend:zhang")
  const suggestion: ApiResponse<ReplySuggestion> = await apiClient.suggestReply("friend:zhang", "请介绍一下试用政策")
  const sent: ApiResponse<SendReplyResult> = await apiClient.sendConversationReply("friend:zhang", "您好，稍后为您介绍。")
  const updatedControl: ApiResponse<ConversationControl> = await apiClient.updateConversationControl("friend:zhang", {
    human_takeover: true,
  })
  const customers: ApiResponse<Customer[]> = await apiClient.listCustomers()
  const customer: ApiResponse<Customer> = await apiClient.getCustomer("user_001")
  const identityDrafts: ApiResponse<IdentityDraft[]> = await apiClient.listIdentityDrafts()
  const identityCandidates: ApiResponse<IdentityCandidate[]> = await apiClient.listIdentityCandidates()
  const selfIdentity: ApiResponse<SelfIdentity> = await apiClient.getGlobalSelfIdentity()
  const updatedSelfIdentity: ApiResponse<SelfIdentity> = await apiClient.updateGlobalSelfIdentity({
    display_name: "碱水",
    identity_facts: ["我是产品顾问"],
  })
  const knowledgeStatus: ApiResponse<import("@/lib/api").KnowledgeStatus> = await apiClient.getKnowledgeStatus()
  const knowledgeSearch: ApiResponse<KnowledgeSearchResult[]> = await apiClient.searchKnowledge("试用政策", 5)
  const knowledgeImport: ApiResponse<KnowledgeImportResult> = await apiClient.importKnowledgeFiles([
    "C:\\docs\\product.pdf",
  ])
  const webKnowledge: ApiResponse<WebKnowledgeBuildResult> = await apiClient.buildWebKnowledgeFromDocuments([
    "C:\\docs\\brief.docx",
  ], 3)
  const patch: SettingsPatch = { reply_style: "专业友好", sensitive_message_review: true }
  const controlPatch: ConversationControlPatch = { paused: true }
  const selfIdentityPatch: SelfIdentityPatch = { identity_facts: ["默认保持专业友好"] }
  const eventsUrl: string = buildEventsUrl({ replay: 5 })
  const eventSourceFactory: typeof createEventSource = createEventSource

  return {
    dashboard,
    runtime,
    environment,
    started,
    stopped,
    restarted,
    settings,
    updatedSettings,
    privacy,
    updatedPrivacy,
    conversations,
    conversation,
    control,
    suggestion,
    sent,
    updatedControl,
    customers,
    customer,
    identityDrafts,
    identityCandidates,
    selfIdentity,
    updatedSelfIdentity,
    knowledgeStatus,
    knowledgeSearch,
    knowledgeImport,
    webKnowledge,
    patch,
    controlPatch,
    selfIdentityPatch,
    eventsUrl,
    eventSourceFactory,
  }
}

void assertApiClientContract
