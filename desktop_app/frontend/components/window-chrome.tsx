import type { ReactNode } from "react"

interface WindowChromeProps {
  title?: string
  rightSlot?: ReactNode
}

export function WindowChrome({ title, rightSlot }: WindowChromeProps) {
  return (
    <div className="flex h-16 items-center bg-[var(--app-sidebar-bg)] px-7">
      <div className="flex items-center gap-2.5">
        <span className="h-3.5 w-3.5 rounded-full bg-[#ff5f56]" aria-hidden />
        <span className="h-3.5 w-3.5 rounded-full bg-[#ffbd2e]" aria-hidden />
        <span className="h-3.5 w-3.5 rounded-full bg-[#27c93f]" aria-hidden />
      </div>
      {title ? <div className="ml-8 text-[22px] font-bold text-[var(--app-title)]">{title}</div> : null}
      {rightSlot && <div className="ml-auto">{rightSlot}</div>}
    </div>
  )
}
