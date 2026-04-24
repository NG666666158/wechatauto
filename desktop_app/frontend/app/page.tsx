import type { ReactNode } from "react"
import { AppShell } from "@/components/app-shell"
import {
  Bell,
  Bot,
  CheckCircle2,
  ChevronRight,
  ListTodo,
  MessageCircle,
  Play,
  Settings,
  UserPlus,
  Users,
} from "lucide-react"

const text = {
  title: "\u9996\u9875",
  syncOk: "\u540c\u6b65\u6b63\u5e38",
  wechatConnection: "\u5fae\u4fe1\u8fde\u63a5\u72b6\u6001",
  connected: "\u5df2\u8fde\u63a5",
  wechatOnline: "\u5fae\u4fe1\u5728\u7ebf",
  autoReplyStatus: "\u81ea\u52a8\u56de\u590d\u72b6\u6001",
  running: "\u8fd0\u884c\u4e2d",
  autoReplyOn: "\u81ea\u52a8\u56de\u590d\u5df2\u5f00\u542f",
  todayVisitors: "\u4eca\u65e5\u63a5\u5f85",
  todayReplies: "\u4eca\u65e5\u56de\u590d",
  pendingItems: "\u5f85\u5904\u7406\u4e8b\u9879",
  comparedYesterday18: "\u8f83\u6628\u65e5 +18",
  comparedYesterday32: "\u8f83\u6628\u65e5 +32",
  needsProcessing: "\u9700\u8981\u53ca\u65f6\u5904\u7406",
  quickActions: "\u5feb\u6377\u64cd\u4f5c",
  startPause: "\u542f\u52a8/\u6682\u505c\u81ea\u52a8\u56de\u590d",
  viewPending: "\u67e5\u770b\u5f85\u5904\u7406",
  goSettings: "\u8fdb\u5165\u8bbe\u7f6e",
  recentActivity: "\u6700\u8fd1\u52a8\u6001",
  activity1: "\u65b0\u5ba2\u6237\u54a8\u8be2\uff1a\u8bf7\u95ee\u4f60\u4eec\u7684\u4ea7\u54c1\u652f\u6301\u8bd5\u7528\u5417\uff1f",
  activity2: "\u81ea\u52a8\u56de\u590d\u5df2\u53d1\u9001\u7ed9\uff1a\u5f20\u5148\u751f",
  activity3: "\u5ba2\u6237\u7b49\u5f85\u4eba\u5de5\u63a5\u7ba1\uff1a\u674e\u5973\u58eb\uff08\u9700\u8981\u4f18\u60e0\u65b9\u6848\uff09",
  viewMore: "\u67e5\u770b\u66f4\u591a",
}

export default function HomePage() {
  return (
    <AppShell
      title={text.title}
      headerRight={
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2 font-medium text-emerald-600">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>{text.syncOk}</span>
          </div>
          <span className="font-medium text-[var(--app-muted-text)] tabular-nums">09:45:32</span>
        </div>
      }
    >
      <div className="space-y-5 p-7">
        <div className="grid grid-cols-5 gap-4">
          <StatusCard
            label={text.wechatConnection}
            icon={<CheckCircle2 className="h-6 w-6 text-emerald-500" />}
            value={text.connected}
            sub={text.wechatOnline}
            valueClass="text-emerald-600"
          />
          <StatusCard
            label={text.autoReplyStatus}
            icon={<Play className="h-6 w-6 fill-blue-500 text-blue-500" />}
            value={text.running}
            sub={text.autoReplyOn}
            valueClass="text-blue-600"
          />
          <StatusCard
            label={text.todayVisitors}
            icon={<Users className="h-6 w-6 text-orange-500" />}
            value="128"
            sub={text.comparedYesterday18}
            valueClass="text-[var(--app-strong-text)]"
            accentClass="text-orange-500"
            isNumber
          />
          <StatusCard
            label={text.todayReplies}
            icon={<MessageCircle className="h-6 w-6 text-violet-500" />}
            value="256"
            sub={text.comparedYesterday32}
            valueClass="text-[var(--app-strong-text)]"
            accentClass="text-violet-500"
            isNumber
          />
          <StatusCard
            label={text.pendingItems}
            icon={<Bell className="h-6 w-6 text-rose-500" />}
            value="12"
            sub={text.needsProcessing}
            valueClass="text-[var(--app-strong-text)]"
            accentClass="text-rose-500"
            isNumber
          />
        </div>

        <section className="rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] p-5 shadow-[var(--app-card-shadow)]">
          <h2 className="mb-3 text-[17px] font-bold text-[var(--app-title)]">{text.quickActions}</h2>
          <div className="grid grid-cols-3 gap-5">
            <QuickAction
              icon={<Play className="h-5 w-5 fill-white text-white" />}
              iconBg="bg-emerald-500"
              label={text.startPause}
            />
            <QuickAction icon={<ListTodo className="h-5 w-5 text-white" />} iconBg="bg-orange-500" label={text.viewPending} />
            <QuickAction icon={<Settings className="h-5 w-5 text-white" />} iconBg="bg-blue-500" label={text.goSettings} />
          </div>
        </section>

        <section className="rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] p-5 shadow-[var(--app-card-shadow)]">
          <h2 className="mb-3 text-[17px] font-bold text-[var(--app-title)]">{text.recentActivity}</h2>
          <ul className="divide-y divide-[var(--app-row-border)]">
            <ActivityItem icon={<UserPlus className="h-4 w-4 text-emerald-500" />} text={text.activity1} time="09:41" />
            <ActivityItem icon={<Bot className="h-4 w-4 text-blue-500" />} text={text.activity2} time="09:39" />
            <ActivityItem icon={<UserPlus className="h-4 w-4 text-orange-500" />} text={text.activity3} time="09:35" />
          </ul>
          <div className="mt-4 flex justify-end">
            <button className="flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700">
              {text.viewMore}
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </section>
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
        <span className={`${valueClass} ${isNumber ? "text-2xl font-semibold leading-none" : "text-lg font-bold"}`}>
          {value}
        </span>
      </div>
      <div className="mt-3 text-xs font-medium text-[var(--app-muted-text)]">{sub}</div>
    </div>
  )
}

function QuickAction({ icon, iconBg, label }: { icon: ReactNode; iconBg: string; label: string }) {
  return (
    <button className="flex h-14 items-center justify-center gap-3 rounded-lg border border-[var(--app-action-border)] bg-[var(--app-action-bg)] px-5 text-left transition-colors hover:border-blue-300 hover:bg-[var(--app-action-hover-bg)]">
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
