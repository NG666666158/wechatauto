"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { EmptyState, ErrorState, LoadingState } from "@/components/api-state"
import { UserAvatar } from "@/components/user-avatar"
import { apiClient } from "@/lib/api"
import type { Customer, IdentityCandidate, IdentityDraft, SelfIdentity } from "@/lib/api"
import { ChevronRight, Pencil, Plus, Save, Search, Sparkles } from "lucide-react"

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [drafts, setDrafts] = useState<IdentityDraft[]>([])
  const [candidates, setCandidates] = useState<IdentityCandidate[]>([])
  const [selfIdentity, setSelfIdentity] = useState<SelfIdentity | null>(null)
  const [selfName, setSelfName] = useState("")
  const [selfFactsText, setSelfFactsText] = useState("")
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [savingSelf, setSavingSelf] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  async function loadInitialData() {
    setLoading(true)
    setError("")
    try {
      const [customersResponse, draftsResponse, candidatesResponse, selfResponse] = await Promise.all([
        apiClient.listCustomers(),
        apiClient.listIdentityDrafts(),
        apiClient.listIdentityCandidates(),
        apiClient.getGlobalSelfIdentity(),
      ])
      if (!customersResponse.success || !customersResponse.data) {
        setError(customersResponse.error ? `${customersResponse.error.code}: ${customersResponse.error.message}` : "客户列表加载失败")
        return
      }
      const customerList = customersResponse.data
      setCustomers(customerList)
      setSelectedId((current) => current || customerList[0]?.customer_id || "")
      setDrafts(draftsResponse.success && draftsResponse.data ? draftsResponse.data : [])
      setCandidates(candidatesResponse.success && candidatesResponse.data ? candidatesResponse.data : [])
      if (selfResponse.success && selfResponse.data) {
        setSelfIdentity(selfResponse.data)
        setSelfName(selfResponse.data.display_name)
        setSelfFactsText(selfResponse.data.identity_facts.join("\n"))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接本地后端服务")
    } finally {
      setLoading(false)
    }
  }

  async function loadCustomer(customerId: string) {
    if (!customerId) {
      setSelectedCustomer(null)
      return
    }
    setLoadingDetail(true)
    setError("")
    try {
      const response = await apiClient.getCustomer(customerId)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "客户详情加载失败")
        return
      }
      setSelectedCustomer(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法读取客户详情")
    } finally {
      setLoadingDetail(false)
    }
  }

  async function saveSelfIdentity() {
    setSavingSelf(true)
    setError("")
    setNotice("")
    const facts = selfFactsText
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
    try {
      const response = await apiClient.updateGlobalSelfIdentity({
        display_name: selfName.trim() || "未命名身份",
        identity_facts: facts,
      })
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "自我身份保存失败")
        return
      }
      setSelfIdentity(response.data)
      setSelfName(response.data.display_name)
      setSelfFactsText(response.data.identity_facts.join("\n"))
      setNotice("自我身份已保存，后续回复会优先使用这份全局身份事实。")
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法保存自我身份")
    } finally {
      setSavingSelf(false)
    }
  }

  useEffect(() => {
    void loadInitialData()
  }, [])

  useEffect(() => {
    void loadCustomer(selectedId)
  }, [selectedId])

  const filteredCustomers = customers.filter((customer) => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return true
    return `${customer.display_name} ${customer.status} ${customer.tags.join(" ")} ${customer.remark}`.toLowerCase().includes(keyword)
  })

  return (
    <AppShell title="客户">
      <div className="flex min-h-[656px] flex-1">
        <aside className="w-[270px] shrink-0 border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="mb-3 text-[15px] font-semibold text-slate-800">客户列表</h2>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索客户、标签或备注"
                className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-4">
              <LoadingState label="正在加载客户" />
            </div>
          ) : filteredCustomers.length ? (
            <ul>
              {filteredCustomers.map((customer) => (
                <CustomerRow
                  key={customer.customer_id}
                  customer={customer}
                  active={customer.customer_id === selectedId}
                  onClick={() => setSelectedId(customer.customer_id)}
                />
              ))}
            </ul>
          ) : (
            <div className="p-4">
              <EmptyState title="暂无客户" />
            </div>
          )}

          <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            <span>共 {customers.length} 位客户</span>
            <div className="flex items-center gap-1">
              <span>1</span>
              <span className="text-slate-400">/ 1</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </div>
          </div>
        </aside>

        <section className="flex-1 border-r border-slate-200 bg-white p-6">
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          {notice ? <div className="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</div> : null}
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[15px] font-semibold text-slate-800">客户详情</h2>
            <button className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 text-slate-400 hover:bg-slate-50">
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>

          {loadingDetail ? (
            <LoadingState label="正在加载客户详情" />
          ) : selectedCustomer ? (
            <CustomerDetail customer={selectedCustomer} />
          ) : (
            <EmptyState title="请选择客户" />
          )}

          <SelfIdentityCard
            className="mt-6"
            identity={selfIdentity}
            name={selfName}
            factsText={selfFactsText}
            saving={savingSelf}
            onNameChange={setSelfName}
            onFactsChange={setSelfFactsText}
            onSave={saveSelfIdentity}
          />
        </section>

        <aside className="w-[320px] shrink-0 bg-slate-50/40 p-6">
          <h2 className="mb-4 text-[15px] font-semibold text-slate-800">待确认客户</h2>
          <div className="space-y-3">
            <PendingCard
              title={`身份草稿（${drafts.length} 条）`}
              text={drafts[0] ? `待确认用户：${drafts[0].draft_user_id}` : "暂无新身份草稿"}
              kind="draft"
            />
            <PendingCard
              title={`疑似重复客户（${candidates.length} 条）`}
              text={candidates[0] ? `候选项：${candidates[0].candidate_id}` : "暂无疑似重复客户"}
              kind="candidate"
            />
          </div>
          <button className="mt-4 flex w-full items-center justify-center gap-1 text-xs text-blue-600 hover:text-blue-700">
            查看全部身份任务
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </aside>
      </div>
    </AppShell>
  )
}

function CustomerRow({ customer, active, onClick }: { customer: Customer; active: boolean; onClick: () => void }) {
  const primaryTag = customer.tags[0] || statusText(customer.status)
  return (
    <li
      onClick={onClick}
      className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-5 py-3 ${
        active ? "bg-blue-50/70" : "hover:bg-slate-50"
      }`}
    >
      <UserAvatar name={customer.display_name || customer.customer_id} size={36} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-slate-800">{customer.display_name || customer.customer_id}</div>
        <div className="mt-0.5 truncate text-xs text-slate-400">{formatDate(customer.last_contact_at)}</div>
      </div>
      <span className={`rounded px-2 py-0.5 text-[11px] ${tagClass(primaryTag)}`}>{primaryTag}</span>
    </li>
  )
}

function CustomerDetail({ customer }: { customer: Customer }) {
  return (
    <>
      <div className="mb-6 flex items-center gap-4">
        <UserAvatar name={customer.display_name || customer.customer_id} size={56} />
        <div>
          <div className="text-[17px] font-semibold text-slate-800">{customer.display_name || customer.customer_id}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {(customer.tags.length ? customer.tags : [statusText(customer.status)]).map((tag) => (
              <span key={tag} className={`rounded px-2 py-0.5 text-xs ${tagClass(tag)}`}>{tag}</span>
            ))}
          </div>
        </div>
      </div>

      <dl className="space-y-4 text-sm">
        <Field label="客户 ID" value={customer.customer_id} />
        <Field label="客户名称" value={customer.display_name || "未命名客户"} />
        <Field
          label="标签"
          value={
            <div className="flex flex-wrap items-center gap-1.5">
              {(customer.tags.length ? customer.tags : [statusText(customer.status)]).map((tag) => (
                <span key={tag} className={`rounded px-2 py-0.5 text-xs ${tagClass(tag)}`}>{tag}</span>
              ))}
              <button className="flex h-5 w-5 items-center justify-center rounded-full border border-dashed border-slate-300 text-slate-400">
                <Plus className="h-3 w-3" />
              </button>
            </div>
          }
        />
        <Field label="备注" value={customer.remark || "暂无备注，可在后续客户编辑阶段补充。"} />
        <Field label="常见需求" value={deriveNeeds(customer)} />
        <Field label="最近联系" value={formatDate(customer.last_contact_at)} />
        <Field label="来源渠道" value="微信会话 / 身份识别链路" />
        <Field label="当前状态" value={statusText(customer.status)} />
      </dl>
    </>
  )
}

function SelfIdentityCard({
  className,
  identity,
  name,
  factsText,
  saving,
  onNameChange,
  onFactsChange,
  onSave,
}: {
  className?: string
  identity: SelfIdentity | null
  name: string
  factsText: string
  saving: boolean
  onNameChange: (value: string) => void
  onFactsChange: (value: string) => void
  onSave: () => void
}) {
  return (
    <div className={`rounded-2xl border border-blue-100 bg-blue-50/40 p-5 ${className ?? ""}`}>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-[15px] font-semibold text-slate-800">
            <Sparkles className="h-4 w-4 text-blue-500" />
            自我身份
          </div>
          <p className="mt-1 text-xs text-slate-500">这是全局默认身份，面对老师、父母等关系身份会在后续层级中叠加。</p>
        </div>
        <button
          disabled={saving}
          onClick={onSave}
          className="flex h-8 items-center gap-1.5 rounded-lg bg-blue-500 px-3 text-xs font-medium text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "保存中" : "保存"}
        </button>
      </div>
      <div className="grid gap-3">
        <label className="text-xs font-medium text-slate-600">
          显示名称
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder={identity?.display_name || "例如：碱水"}
            className="mt-1 h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 focus:border-blue-400 focus:outline-none"
          />
        </label>
        <label className="text-xs font-medium text-slate-600">
          身份事实（一行一条）
          <textarea
            value={factsText}
            onChange={(event) => onFactsChange(event.target.value)}
            rows={4}
            placeholder="例如：我是产品顾问&#10;面对客户时保持专业友好"
            className="mt-1 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed text-slate-800 focus:border-blue-400 focus:outline-none"
          />
        </label>
      </div>
    </div>
  )
}

function PendingCard({ title, text, kind }: { title: string; text: string; kind: "draft" | "candidate" }) {
  const dotClass = kind === "draft" ? "bg-blue-500" : "bg-purple-500"
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-1 flex items-center gap-1.5 text-sm font-medium text-slate-800">
        <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
        {title}
      </div>
      <p className="mb-3 text-xs text-slate-500">{text}</p>
      <div className="flex gap-2">
        <button className="flex-1 rounded-md bg-blue-500 py-1.5 text-xs font-medium text-white hover:bg-blue-600">确认</button>
        <button className="flex-1 rounded-md border border-slate-200 bg-white py-1.5 text-xs text-slate-600 hover:bg-slate-50">忽略</button>
        <button className="flex-1 rounded-md border border-slate-200 bg-white py-1.5 text-xs text-slate-600 hover:bg-slate-50">合并</button>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start gap-6">
      <dt className="w-20 shrink-0 text-slate-500">{label}</dt>
      <dd className="flex-1 text-slate-800">{value}</dd>
    </div>
  )
}

function statusText(status: string) {
  const normalized = status.toLowerCase()
  if (normalized === "intent") return "意向客户"
  if (normalized === "follow_up") return "跟进中"
  if (normalized === "confirmed") return "已确认"
  if (normalized === "not_found") return "未找到"
  return status || "未分类"
}

function tagClass(tag: string) {
  if (tag.includes("高")) return "bg-orange-100 text-orange-600"
  if (tag.includes("潜在") || tag.includes("跟进")) return "bg-blue-100 text-blue-600"
  if (tag.includes("意向") || tag.includes("确认")) return "bg-emerald-100 text-emerald-600"
  return "bg-slate-100 text-slate-500"
}

function deriveNeeds(customer: Customer) {
  const text = `${customer.remark} ${customer.tags.join(" ")}`
  if (text.includes("试用")) return "产品试用、功能介绍、价格方案"
  if (text.includes("优惠")) return "优惠方案、交付周期、售后政策"
  return "待从后续会话中自动归纳"
}

function formatDate(value: string | null | undefined) {
  if (!value) return "暂无记录"
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
