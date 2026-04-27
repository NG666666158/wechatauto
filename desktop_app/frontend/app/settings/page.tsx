"use client"

import type { ReactNode } from "react"
import { useEffect, useState, useTransition } from "react"
import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingState } from "@/components/api-state"
import { apiClient } from "@/lib/api"
import { getDesktopShellBridge, type DesktopShellPreferences } from "@/lib/electron-shell"
import type { PrivacyPolicy, Settings, SettingsPatch } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  ChevronDown,
  ChevronRight,
  Clock,
  DatabaseBackup,
  FileClock,
  Info,
  KeyRound,
  MessageSquare,
  Power,
  ShieldAlert,
  ShieldBan,
  UserPlus,
} from "lucide-react"

const tabs = ["基础设置", "回复设置", "客户管理", "高级设置"] as const
const replyStyles = ["专业友好", "自然轻松", "简洁高效"] as const

const advancedItems = [
  { label: "关键词管理", icon: KeyRound },
  { label: "黑名单管理", icon: ShieldBan },
  { label: "数据备份与恢复", icon: DatabaseBackup },
  { label: "日志管理", icon: FileClock },
  { label: "系统信息", icon: Info },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("基础设置")
  const [settings, setSettings] = useState<Settings | null>(null)
  const [privacy, setPrivacy] = useState<PrivacyPolicy | null>(null)
  const [desktopPreferences, setDesktopPreferences] = useState<DesktopShellPreferences | null>(null)
  const [desktopShellAvailable, setDesktopShellAvailable] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  async function loadSettings() {
    setError("")
    const shellBridge = getDesktopShellBridge()
    const [settingsResponse, privacyResponse, shellPreferences] = await Promise.all([
      apiClient.getSettings(),
      apiClient.getPrivacyPolicy(),
      shellBridge.getPreferences(),
    ])
    if (!settingsResponse.success || !privacyResponse.success) {
      const failed = !settingsResponse.success ? settingsResponse : privacyResponse
      setError(failed.error ? `${failed.error.code}: ${failed.error.message}` : "设置数据加载失败")
    }
    setSettings(settingsResponse.data)
    setPrivacy(privacyResponse.data)
    setDesktopShellAvailable(shellBridge.isAvailable())
    setDesktopPreferences(shellPreferences)
    setLoading(false)
  }

  useEffect(() => {
    void loadSettings().catch((err: unknown) => {
      setLoading(false)
      setError(err instanceof Error ? err.message : "无法连接本地后端服务")
    })
  }, [])

  function updateSettings(patch: SettingsPatch, successMessage = "设置已保存") {
    startTransition(async () => {
      setError("")
      setMessage("")
      const response = await apiClient.updateSettings(patch)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "设置保存失败")
        return
      }
      setSettings(response.data)
      setPrivacy(response.data.privacy)
      setMessage(successMessage)
    })
  }

  function updatePrivacy(patch: Partial<PrivacyPolicy>, successMessage = "隐私策略已保存") {
    startTransition(async () => {
      setError("")
      setMessage("")
      const response = await apiClient.updatePrivacyPolicy(patch)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "隐私策略保存失败")
        return
      }
      setPrivacy(response.data)
      setSettings((current) => (current ? { ...current, privacy: response.data as PrivacyPolicy } : current))
      setMessage(successMessage)
    })
  }

  function updateDesktopPreferences(
    patch: Partial<DesktopShellPreferences>,
    successMessage = "桌面偏好已保存",
  ) {
    const shellBridge = getDesktopShellBridge()
    if (!shellBridge.isAvailable()) {
      setError("当前不在 Electron 桌面端环境，无法保存桌面偏好")
      return
    }
    startTransition(async () => {
      setError("")
      setMessage("")
      const nextPreferences = await shellBridge.updatePreferences(patch)
      if (!nextPreferences) {
        setError("桌面偏好保存失败")
        return
      }
      setDesktopPreferences(nextPreferences)
      setDesktopShellAvailable(true)
      setMessage(successMessage)
    })
  }

  function setSensitiveReview(nextValue: boolean) {
    if (!nextValue && !window.confirm("关闭敏感消息先审核后，自动回复可能直接发出高风险内容。确认关闭吗？")) {
      return
    }
    updateSettings({ sensitive_message_review: nextValue }, nextValue ? "敏感审核已开启" : "敏感审核已关闭")
  }

  return (
    <AppShell title="设置">
      <div className="flex min-h-[656px] flex-1">
        <section className="flex-1 p-8">
          <div className="mb-6 flex gap-6 border-b border-slate-200">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "relative pb-3 text-sm transition-colors",
                  activeTab === tab ? "font-semibold text-blue-600" : "text-slate-500 hover:text-slate-700",
                )}
              >
                {tab}
                {activeTab === tab ? <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-blue-500" /> : null}
              </button>
            ))}
          </div>

          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          {message ? (
            <div className="mb-4 rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
              {message}
            </div>
          ) : null}

          {loading ? (
            <LoadingState label="正在读取本地设置" />
          ) : settings && privacy ? (
            <div className="space-y-3">
              {activeTab === "基础设置" ? (
                <BaseSettings
                  settings={settings}
                  privacy={privacy}
                  pending={isPending}
                  updateSettings={updateSettings}
                  updatePrivacy={updatePrivacy}
                  setSensitiveReview={setSensitiveReview}
                />
              ) : null}
              {activeTab === "回复设置" ? (
                <ReplySettings settings={settings} pending={isPending} updateSettings={updateSettings} />
              ) : null}
              {activeTab === "客户管理" ? (
                <CustomerSettings settings={settings} pending={isPending} updateSettings={updateSettings} />
              ) : null}
              {activeTab === "高级设置" ? (
                <AdvancedSettings
                  settings={settings}
                  privacy={privacy}
                  desktopPreferences={desktopPreferences}
                  desktopShellAvailable={desktopShellAvailable}
                  pending={isPending}
                  updateSettings={updateSettings}
                  updatePrivacy={updatePrivacy}
                  updateDesktopPreferences={updateDesktopPreferences}
                />
              ) : null}
            </div>
          ) : (
            <ErrorState message="设置数据为空，请确认后端服务是否运行。" />
          )}
        </section>

        <aside className="w-[280px] shrink-0 border-l border-slate-200 bg-slate-50/40 p-6">
          <div className="mb-4">
            <h2 className="text-[15px] font-semibold text-slate-800">
              高级设置 <span className="ml-1 text-xs font-normal text-slate-400">可选</span>
            </h2>
          </div>
          <ul className="space-y-2">
            {advancedItems.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.label}>
                  <button className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 hover:border-blue-200 hover:bg-blue-50/40">
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-slate-500" />
                      {item.label}
                    </span>
                    <ChevronRight className="h-4 w-4 text-slate-400" />
                  </button>
                </li>
              )
            })}
          </ul>
          <DesktopPreferenceSummary
            desktopPreferences={desktopPreferences}
            desktopShellAvailable={desktopShellAvailable}
          />
        </aside>
      </div>
    </AppShell>
  )
}

function BaseSettings({
  settings,
  privacy,
  pending,
  updateSettings,
  updatePrivacy,
  setSensitiveReview,
}: {
  settings: Settings
  privacy: PrivacyPolicy
  pending: boolean
  updateSettings: (patch: SettingsPatch, successMessage?: string) => void
  updatePrivacy: (patch: Partial<PrivacyPolicy>, successMessage?: string) => void
  setSensitiveReview: (nextValue: boolean) => void
}) {
  return (
    <>
      <SettingRow
        iconBg="bg-emerald-500"
        icon={<Power className="h-5 w-5 text-white" />}
        title="自动回复开关"
        desc="开启后将自动回复客户消息"
        right={<Switch checked={settings.auto_reply_enabled} disabled={pending} onChange={(value) => updateSettings({ auto_reply_enabled: value })} />}
      />
      <SettingRow
        iconBg="bg-blue-500"
        icon={<Clock className="h-5 w-5 text-white" />}
        title="工作时间"
        desc="仅在工作时间自动回复"
        right={
          <div className="flex items-center gap-2">
            <TimeInput value={settings.work_hours.start} disabled={pending} onChange={(value) => updateSettings({ work_hours: { ...settings.work_hours, start: value } })} />
            <span className="text-xs text-slate-400">-</span>
            <TimeInput value={settings.work_hours.end} disabled={pending} onChange={(value) => updateSettings({ work_hours: { ...settings.work_hours, end: value } })} />
          </div>
        }
      />
      <SettingRow
        iconBg="bg-violet-500"
        icon={<MessageSquare className="h-5 w-5 text-white" />}
        title="回复风格"
        desc="设置自动回复的话术风格"
        right={
          <SelectValue
            value={settings.reply_style || "专业友好"}
            disabled={pending}
            options={replyStyles}
            onChange={(value) => updateSettings({ reply_style: value })}
          />
        }
      />
      <SettingRow
        iconBg="bg-orange-500"
        icon={<UserPlus className="h-5 w-5 text-white" />}
        title="新客户自动建档"
        desc="新客户咨询时自动创建客户档案"
        right={<Switch checked={settings.new_customer_auto_create} disabled={pending} onChange={(value) => updateSettings({ new_customer_auto_create: value })} />}
      />
      <SettingRow
        iconBg="bg-rose-500"
        icon={<ShieldAlert className="h-5 w-5 text-white" />}
        title="敏感消息先审核"
        desc="涉及敏感内容的消息需人工审核后回复"
        right={<Switch checked={settings.sensitive_message_review} disabled={pending} onChange={setSensitiveReview} />}
      />
      <SettingRow
        iconBg="bg-slate-600"
        icon={<FileClock className="h-5 w-5 text-white" />}
        title="日志保留天数"
        desc="自动清理过期日志，降低本地敏感数据残留"
        right={
          <NumberInput
            value={privacy.log_retention_days}
            min={1}
            max={365}
            disabled={pending}
            suffix="天"
            onChange={(value) => updatePrivacy({ log_retention_days: value })}
          />
        }
      />
    </>
  )
}

function ReplySettings({
  settings,
  pending,
  updateSettings,
}: {
  settings: Settings
  pending: boolean
  updateSettings: (patch: SettingsPatch, successMessage?: string) => void
}) {
  return (
    <>
      <SettingRow
        iconBg="bg-violet-500"
        icon={<MessageSquare className="h-5 w-5 text-white" />}
        title="回复风格"
        desc="影响 AI 生成回复时的语气和详略"
        right={<SelectValue value={settings.reply_style || "专业友好"} disabled={pending} options={replyStyles} onChange={(value) => updateSettings({ reply_style: value })} />}
      />
      <SettingRow
        iconBg="bg-blue-500"
        icon={<Clock className="h-5 w-5 text-white" />}
        title="请求超时"
        desc="模型和知识库检索的最长等待时间"
        right={<NumberInput value={settings.request_timeout_seconds} min={1} max={300} disabled={pending} suffix="秒" onChange={(value) => updateSettings({ request_timeout_seconds: value })} />}
      />
      <SettingRow
        iconBg="bg-emerald-500"
        icon={<Power className="h-5 w-5 text-white" />}
        title="重试次数"
        desc="网络或模型临时失败时的自动重试次数"
        right={<NumberInput value={settings.retry_attempts} min={0} max={10} disabled={pending} suffix="次" onChange={(value) => updateSettings({ retry_attempts: value })} />}
      />
    </>
  )
}

function CustomerSettings({
  settings,
  pending,
  updateSettings,
}: {
  settings: Settings
  pending: boolean
  updateSettings: (patch: SettingsPatch, successMessage?: string) => void
}) {
  return (
    <>
      <SettingRow
        iconBg="bg-orange-500"
        icon={<UserPlus className="h-5 w-5 text-white" />}
        title="新客户自动建档"
        desc="从新会话中自动生成客户初始档案"
        right={<Switch checked={settings.new_customer_auto_create} disabled={pending} onChange={(value) => updateSettings({ new_customer_auto_create: value })} />}
      />
      <SettingRow
        iconBg="bg-rose-500"
        icon={<ShieldBan className="h-5 w-5 text-white" />}
        title="黑名单数量"
        desc="黑名单会话不会自动回复"
        right={<DropdownValue>{settings.blacklist.length} 个</DropdownValue>}
      />
      <SettingRow
        iconBg="bg-slate-600"
        icon={<UserPlus className="h-5 w-5 text-white" />}
        title="人工接管会话"
        desc="人工接管后该会话由客服手动处理"
        right={<DropdownValue>{settings.human_takeover_sessions.length} 个</DropdownValue>}
      />
    </>
  )
}

function AdvancedSettings({
  settings,
  privacy,
  desktopPreferences,
  desktopShellAvailable,
  pending,
  updateSettings,
  updatePrivacy,
  updateDesktopPreferences,
}: {
  settings: Settings
  privacy: PrivacyPolicy
  desktopPreferences: DesktopShellPreferences | null
  desktopShellAvailable: boolean
  pending: boolean
  updateSettings: (patch: SettingsPatch, successMessage?: string) => void
  updatePrivacy: (patch: Partial<PrivacyPolicy>, successMessage?: string) => void
  updateDesktopPreferences: (patch: Partial<DesktopShellPreferences>, successMessage?: string) => void
}) {
  return (
    <>
      <SettingRow
        iconBg="bg-slate-600"
        icon={<Power className="h-5 w-5 text-white" />}
        title="后台静默运行"
        desc="关闭窗口后保持守护服务继续运行"
        right={<Switch checked={settings.run_silently} disabled={pending} onChange={(value) => updateSettings({ run_silently: value })} />}
      />
      <SettingRow
        iconBg="bg-rose-500"
        icon={<ShieldAlert className="h-5 w-5 text-white" />}
        title="强制停止热键"
        desc="运行中可随时按下该热键强制停止自动回复，输入 off 可关闭"
        right={
          <TextInput
            value={settings.force_stop_hotkey || "ctrl+shift+f12"}
            disabled={pending}
            placeholder="ctrl+shift+f12"
            onChange={(value) => updateSettings({ force_stop_hotkey: value.trim() || "off" }, "强制停止热键已保存")}
          />
        }
      />
      <SettingRow
        iconBg="bg-emerald-500"
        icon={<Power className="h-5 w-5 text-white" />}
        title="开机自启"
        desc={desktopShellAvailable ? "系统启动后自动拉起桌面应用" : "仅在 Electron 桌面应用内可编辑"}
        right={
          <Switch
            checked={desktopPreferences?.launchAtLogin ?? false}
            disabled={pending || !desktopShellAvailable || !desktopPreferences}
            onChange={(value) => updateDesktopPreferences({ launchAtLogin: value })}
          />
        }
      />
      <SettingRow
        iconBg="bg-amber-500"
        icon={<Clock className="h-5 w-5 text-white" />}
        title="定时巡检间隔"
        desc={desktopShellAvailable ? "桌面壳每隔 N 秒向后端发起一次 schedule tick" : "仅在 Electron 桌面应用内可编辑"}
        right={
          <NumberInput
            value={desktopPreferences?.scheduleTickIntervalSeconds ?? 60}
            min={15}
            max={3600}
            suffix="秒"
            disabled={pending || !desktopShellAvailable || !desktopPreferences}
            onChange={(value) => updateDesktopPreferences({ scheduleTickIntervalSeconds: value })}
          />
        }
      />
      <SettingRow
        iconBg="bg-blue-500"
        icon={<DatabaseBackup className="h-5 w-5 text-white" />}
        title="知识库分块大小"
        desc="影响本地向量库构建粒度"
        right={<NumberInput value={settings.knowledge_chunk_size} min={100} max={20000} disabled={pending} onChange={(value) => updateSettings({ knowledge_chunk_size: value })} />}
      />
      <SettingRow
        iconBg="bg-violet-500"
        icon={<DatabaseBackup className="h-5 w-5 text-white" />}
        title="分块重叠长度"
        desc="适当重叠可提升检索上下文连续性"
        right={<NumberInput value={settings.knowledge_chunk_overlap} min={0} max={5000} disabled={pending} onChange={(value) => updateSettings({ knowledge_chunk_overlap: value })} />}
      />
      <SettingRow
        iconBg="bg-rose-500"
        icon={<ShieldAlert className="h-5 w-5 text-white" />}
        title="记忆保留天数"
        desc="超过期限的记忆数据会在保留策略中清理"
        right={<NumberInput value={privacy.memory_retention_days} min={1} max={3650} disabled={pending} suffix="天" onChange={(value) => updatePrivacy({ memory_retention_days: value })} />}
      />
    </>
  )
}

function DesktopPreferenceSummary({
  desktopPreferences,
  desktopShellAvailable,
}: {
  desktopPreferences: DesktopShellPreferences | null
  desktopShellAvailable: boolean
}) {
  return (
    <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 text-sm font-semibold text-slate-800">桌面偏好快照</div>
      <div className="space-y-3 text-sm text-slate-600">
        <div className="flex items-center justify-between gap-3">
          <span className="text-slate-500">开机自启</span>
          <span className="font-medium text-slate-800">
            {desktopShellAvailable
              ? desktopPreferences?.launchAtLogin
                ? "已开启"
                : "未开启"
              : "仅 Electron 可用"}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-slate-500">定时巡检间隔</span>
          <span className="font-medium text-slate-800">
            {desktopShellAvailable && desktopPreferences
              ? `${desktopPreferences.scheduleTickIntervalSeconds} 秒`
              : "仅 Electron 可用"}
          </span>
        </div>
      </div>
    </div>
  )
}

function SettingRow({
  icon,
  iconBg,
  title,
  desc,
  right,
}: {
  icon: ReactNode
  iconBg: string
  title: string
  desc: string
  right: ReactNode
}) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4">
      <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", iconBg)}>{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-slate-800">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{desc}</div>
      </div>
      <div className="shrink-0">{right}</div>
    </div>
  )
}

function DropdownValue({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700">
      {children}
      <ChevronDown className="h-4 w-4 text-slate-400" />
    </div>
  )
}

function SelectValue({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string
  options: readonly string[]
  disabled?: boolean
  onChange: (value: string) => void
}) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 disabled:opacity-60"
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  )
}

function TimeInput({ value, disabled, onChange }: { value: string; disabled?: boolean; onChange: (value: string) => void }) {
  return (
    <input
      type="time"
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 w-[112px] rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 disabled:opacity-60"
    />
  )
}

function TextInput({
  value,
  disabled,
  placeholder,
  onChange,
}: {
  value: string
  disabled?: boolean
  placeholder?: string
  onChange: (value: string) => void
}) {
  return (
    <input
      type="text"
      value={value}
      disabled={disabled}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 w-[168px] rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 disabled:opacity-60"
    />
  )
}

function NumberInput({
  value,
  min,
  max,
  suffix,
  disabled,
  onChange,
}: {
  value: number
  min: number
  max: number
  suffix?: string
  disabled?: boolean
  onChange: (value: number) => void
}) {
  return (
    <label className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus-within:border-blue-400">
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-20 bg-transparent text-right outline-none disabled:opacity-60"
      />
      {suffix ? <span className="text-xs text-slate-400">{suffix}</span> : null}
    </label>
  )
}

function Switch({ checked, disabled, onChange }: { checked: boolean; disabled?: boolean; onChange: (value: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        checked ? "bg-blue-500" : "bg-slate-200",
      )}
    >
      <span className={cn("inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform", checked ? "translate-x-[22px]" : "translate-x-0.5")} />
    </button>
  )
}
