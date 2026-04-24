import type { ReactNode } from "react"
import { AppShell } from "@/components/app-shell"
import { UserAvatar } from "@/components/user-avatar"
import {
  ImageIcon,
  MessageSquareText,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Send,
  Smile,
  Sparkles,
} from "lucide-react"

const conversations = [
  { name: "张先生", msg: "请问你们的产品支持试用吗？", time: "09:41", unread: 1, active: true },
  { name: "李女士", msg: "价格是多少？", time: "09:39", unread: 2 },
  { name: "王先生", msg: "有相关资料可以看吗？", time: "09:35" },
  { name: "陈小姐", msg: "什么时候可以发货？", time: "09:28" },
  { name: "刘先生", msg: "售后服务包括哪些内容？", time: "09:20" },
]

export default function MessagesPage() {
  return (
    <AppShell title="消息">
      <div className="flex h-[760px]">
        <aside className="w-[280px] shrink-0 border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="mb-3 text-[15px] font-semibold text-slate-800">会话列表</h2>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                placeholder="搜索客户或内容"
                className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>
          <ul>
            {conversations.map((item) => (
              <li
                key={item.name}
                className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-5 py-3.5 ${
                  item.active ? "bg-blue-50/70" : "hover:bg-slate-50"
                }`}
              >
                <UserAvatar name={item.name} size={40} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-slate-800">{item.name}</span>
                    <span className="shrink-0 text-xs text-slate-400 tabular-nums">{item.time}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-slate-500">{item.msg}</span>
                    {item.unread ? (
                      <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-medium text-white">
                        {item.unread}
                      </span>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </aside>

        <section className="flex flex-1 flex-col bg-[#f6f7f9]">
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
            <div className="flex items-center gap-3">
              <span className="text-[15px] font-semibold text-slate-800">张先生</span>
              <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">微信</span>
            </div>
            <div className="flex items-center gap-3 text-slate-400">
              <span className="text-xs tabular-nums">09:41</span>
              <MoreHorizontal className="h-4 w-4" />
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
            <IncomingBubble name="张先生">请问你们的产品支持试用吗？</IncomingBubble>
            <OutgoingBubble>
              您好，支持免费试用 7 天，试用期间可以体验全部核心功能。
            </OutgoingBubble>
            <IncomingBubble name="张先生" time="09:42">
              好的，那需要如何申请呢？
            </IncomingBubble>
            <OutgoingBubble>
              您可以点击官网“免费试用”按钮，填写信息后我们会尽快为您开通。
            </OutgoingBubble>
          </div>

          <div className="border-t border-slate-200 bg-white px-6 py-3">
            <div className="mb-2 flex items-center gap-3 text-slate-400">
              <Smile className="h-4 w-4" />
              <ImageIcon className="h-4 w-4" />
              <Paperclip className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-3">
              <input
                placeholder="输入消息...（Enter 发送，Ctrl+Enter 换行）"
                className="h-9 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
              />
              <button className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-500 px-4 text-sm font-medium text-white hover:bg-blue-600">
                <Send className="h-4 w-4" />
                发送
              </button>
            </div>
          </div>
        </section>

        <aside className="w-[280px] shrink-0 border-l border-slate-200 bg-white p-5">
          <div className="mb-6 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-blue-600">
              <Sparkles className="h-4 w-4" />
              AI建议回复
            </div>
            <p className="mb-4 text-xs leading-relaxed text-slate-600">
              可以告知试用时长、申请方式，并邀请对方留下联系方式，便于后续跟进。
            </p>
            <div className="space-y-2">
              <button className="w-full rounded-lg bg-blue-500 py-2 text-sm font-medium text-white hover:bg-blue-600">
                一键发送
              </button>
              <button className="w-full rounded-lg border border-slate-200 bg-white py-2 text-sm text-slate-700 hover:bg-slate-50">
                重新生成
              </button>
              <button className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white py-2 text-sm text-slate-700 hover:bg-slate-50">
                <MessageSquareText className="h-4 w-4" />
                人工接管
              </button>
            </div>
          </div>

          <div>
            <div className="mb-3 text-sm font-medium text-slate-800">客户信息</div>
            <dl className="space-y-3 text-xs">
              <InfoRow label="标签">
                <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-600">意向客户</span>
                <button className="flex h-4 w-4 items-center justify-center rounded-full border border-dashed border-slate-300 text-slate-400">
                  <Plus className="h-3 w-3" />
                </button>
              </InfoRow>
              <InfoRow label="状态">
                <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-600">跟进中</span>
              </InfoRow>
              <InfoRow label="最近联系">
                <span className="text-slate-600 tabular-nums">2024-05-20 09:41</span>
              </InfoRow>
            </dl>
          </div>
        </aside>
      </div>
    </AppShell>
  )
}

function IncomingBubble({ name, time, children }: { name: string; time?: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <UserAvatar name={name} size={32} />
      <div>
        <div className="max-w-[430px] rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm">
          {children}
        </div>
        {time ? <div className="mt-1 text-xs text-slate-400">{time}</div> : null}
      </div>
    </div>
  )
}

function OutgoingBubble({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start justify-end gap-2">
      <div className="max-w-[430px]">
        <div className="mb-1 flex items-center justify-end gap-1.5 text-xs text-slate-400">
          <Sparkles className="h-3 w-3" />
          <span>自动回复</span>
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
