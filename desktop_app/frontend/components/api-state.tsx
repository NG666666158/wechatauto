import type { ReactNode } from "react"
import { AlertCircle, Inbox, LoaderCircle } from "lucide-react"

export function LoadingState({ label = "正在加载数据" }: { label?: string }) {
  return (
    <div className="flex min-h-[180px] items-center justify-center rounded-xl border border-[var(--app-card-border)] bg-[var(--app-card-bg)] text-sm font-medium text-[var(--app-muted-text)]">
      <LoaderCircle className="mr-2 h-4 w-4 animate-spin text-blue-500" />
      {label}
    </div>
  )
}

export function ErrorState({ title = "数据暂时不可用", message }: { title?: string; message: string }) {
  return (
    <div className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      <div className="flex items-center gap-2 font-semibold">
        <AlertCircle className="h-4 w-4" />
        {title}
      </div>
      <div className="mt-1 leading-relaxed">{message}</div>
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex min-h-[160px] flex-col items-center justify-center rounded-xl border border-dashed border-[var(--app-card-border)] bg-[var(--app-card-bg)] px-6 text-center">
      <Inbox className="mb-3 h-7 w-7 text-[var(--app-muted-text)]" />
      <div className="text-sm font-semibold text-[var(--app-strong-text)]">{title}</div>
      {children ? <div className="mt-2 text-xs leading-relaxed text-[var(--app-muted-text)]">{children}</div> : null}
    </div>
  )
}
