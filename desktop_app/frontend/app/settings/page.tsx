"use client"

import type { ReactNode } from "react"
import { useState } from "react"
import { AppShell } from "@/components/app-shell"
import { cn } from "@/lib/utils"
import { ChevronDown, ChevronRight, Clock, MessageSquare, Power, ShieldAlert, UserPlus } from "lucide-react"

const tabs = ["基础设置", "回复设置", "客户管理", "高级设置"]
const advancedItems = ["关键词管理", "黑名单管理", "数据备份与恢复", "日志管理", "系统信息"]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("基础设置")
  const [autoReply, setAutoReply] = useState(true)
  const [autoCreate, setAutoCreate] = useState(true)
  const [sensitive, setSensitive] = useState(true)

  return (
    <AppShell title="设置">
      <div className="flex h-[760px]">
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
                {activeTab === tab ? (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-blue-500" />
                ) : null}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            <SettingRow
              iconBg="bg-emerald-500"
              icon={<Power className="h-5 w-5 text-white" />}
              title="自动回复开关"
              desc="开启后将自动回复客户消息"
              right={<Switch checked={autoReply} onChange={setAutoReply} />}
            />
            <SettingRow
              iconBg="bg-blue-500"
              icon={<Clock className="h-5 w-5 text-white" />}
              title="工作时间"
              desc="仅在工作时间自动回复"
              right={
                <DropdownValue>
                  <span className="tabular-nums">09:00 - 18:00</span>
                </DropdownValue>
              }
            />
            <SettingRow
              iconBg="bg-violet-500"
              icon={<MessageSquare className="h-5 w-5 text-white" />}
              title="回复风格"
              desc="设置自动回复的话术风格"
              right={<DropdownValue>专业友好</DropdownValue>}
            />
            <SettingRow
              iconBg="bg-orange-500"
              icon={<UserPlus className="h-5 w-5 text-white" />}
              title="新客户自动建档"
              desc="新客户咨询时自动创建客户档案"
              right={<Switch checked={autoCreate} onChange={setAutoCreate} />}
            />
            <SettingRow
              iconBg="bg-rose-500"
              icon={<ShieldAlert className="h-5 w-5 text-white" />}
              title="敏感消息先审核"
              desc="涉及敏感内容的消息需人工审核后回复"
              right={<Switch checked={sensitive} onChange={setSensitive} />}
            />
          </div>
        </section>

        <aside className="w-[280px] shrink-0 border-l border-slate-200 bg-slate-50/40 p-6">
          <div className="mb-4">
            <h2 className="text-[15px] font-semibold text-slate-800">
              高级设置 <span className="ml-1 text-xs font-normal text-slate-400">（可选）</span>
            </h2>
          </div>
          <ul className="space-y-2">
            {advancedItems.map((item) => (
              <li key={item}>
                <button className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 hover:border-blue-200 hover:bg-blue-50/40">
                  <span>{item}</span>
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </AppShell>
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
      <div className="flex-1">
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

function Switch({ checked, onChange }: { checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
        checked ? "bg-blue-500" : "bg-slate-200",
      )}
    >
      <span
        className={cn(
          "inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
          checked ? "translate-x-[22px]" : "translate-x-0.5",
        )}
      />
    </button>
  )
}
