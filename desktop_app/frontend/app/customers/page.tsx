import type { ReactNode } from "react"
import { AppShell } from "@/components/app-shell"
import { UserAvatar } from "@/components/user-avatar"
import { ChevronRight, Pencil, Plus, Search } from "lucide-react"

const customers = [
  { name: "张先生", tag: "今天 09:41", tagClass: "text-slate-400", active: true },
  { name: "李女士", tag: "高意向", tagClass: "bg-orange-100 text-orange-600" },
  { name: "王先生", tag: "潜在客户", tagClass: "bg-blue-100 text-blue-600" },
  { name: "陈小姐", tag: "一般客户", tagClass: "bg-slate-100 text-slate-500" },
  { name: "刘先生", tag: "意向客户", tagClass: "bg-emerald-100 text-emerald-600" },
]

const pendingCustomers = [
  { title: "疑似重复客户（2条）", text: "可能与 张先生 重复" },
  { title: "疑似重复客户（2条）", text: "可能与 李先生 重复" },
  { title: "疑似重复客户（3条）", text: "可能与 王先生 重复" },
]

export default function CustomersPage() {
  return (
    <AppShell title="客户">
      <div className="flex h-[760px]">
        <aside className="w-[260px] shrink-0 border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="mb-3 text-[15px] font-semibold text-slate-800">客户列表</h2>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                placeholder="搜索客户"
                className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>
          <ul>
            {customers.map((customer) => (
              <li
                key={customer.name}
                className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-5 py-3 ${
                  customer.active ? "bg-blue-50/70" : "hover:bg-slate-50"
                }`}
              >
                <UserAvatar name={customer.name} size={36} />
                <div className="flex-1 text-sm text-slate-800">{customer.name}</div>
                <span className={`rounded px-2 py-0.5 text-[11px] ${customer.tagClass}`}>{customer.tag}</span>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            <span>共 128 位客户</span>
            <div className="flex items-center gap-1">
              <span>1</span>
              <span className="text-slate-400">/ 26</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </div>
          </div>
        </aside>

        <section className="flex-1 border-r border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[15px] font-semibold text-slate-800">客户详情</h2>
            <button className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 text-slate-400 hover:bg-slate-50">
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mb-6 flex items-center gap-4">
            <UserAvatar name="张先生" size={56} />
            <div>
              <div className="text-[17px] font-semibold text-slate-800">张先生</div>
              <div className="mt-1 flex items-center gap-1.5">
                <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">意向客户</span>
                <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-600">线上咨询</span>
              </div>
            </div>
          </div>

          <dl className="space-y-4 text-sm">
            <Field label="客户名称" value="张先生" />
            <Field
              label="标签"
              value={
                <div className="flex items-center gap-1.5">
                  <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">意向客户</span>
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-600">线上咨询</span>
                  <button className="flex h-5 w-5 items-center justify-center rounded-full border border-dashed border-slate-300 text-slate-400">
                    <Plus className="h-3 w-3" />
                  </button>
                </div>
              }
            />
            <Field label="备注" value="关注产品功能与试用政策，预计本周安排演示" />
            <Field label="常见需求" value="产品试用、功能介绍、价格方案" />
            <Field label="最近联系" value="2024-05-20 09:41" />
            <Field label="来源渠道" value="公众号 - 菜单咨询" />
            <Field label="添加时间" value="2024-05-18 15:22" />
          </dl>
        </section>

        <aside className="w-[300px] shrink-0 bg-slate-50/40 p-6">
          <h2 className="mb-4 text-[15px] font-semibold text-slate-800">待确认客户</h2>
          <div className="space-y-3">
            {pendingCustomers.map((item) => (
              <div key={item.text} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="mb-1 flex items-center gap-1.5 text-sm font-medium text-slate-800">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                  {item.title}
                </div>
                <p className="mb-3 text-xs text-slate-500">{item.text}</p>
                <div className="flex gap-2">
                  <button className="flex-1 rounded-md bg-blue-500 py-1.5 text-xs font-medium text-white hover:bg-blue-600">
                    确认
                  </button>
                  <button className="flex-1 rounded-md border border-slate-200 bg-white py-1.5 text-xs text-slate-600 hover:bg-slate-50">
                    忽略
                  </button>
                  <button className="flex-1 rounded-md border border-slate-200 bg-white py-1.5 text-xs text-slate-600 hover:bg-slate-50">
                    合并
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button className="mt-4 flex w-full items-center justify-center gap-1 text-xs text-blue-600 hover:text-blue-700">
            查看全部（7）
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </aside>
      </div>
    </AppShell>
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
