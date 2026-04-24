import type { ReactNode } from "react"
import type { AppThemeKey } from "@/lib/themes"
import { AppSidebar } from "./app-sidebar"
import { WindowChrome } from "./window-chrome"

interface AppShellProps {
  title: string
  headerRight?: ReactNode
  children: ReactNode
  theme?: AppThemeKey
}

export function AppShell({ title, headerRight, children, theme = "classic" }: AppShellProps) {
  return (
    <div className={`app-theme app-theme-${theme} min-h-screen bg-[var(--app-page-bg)] p-6 text-[var(--app-text)]`}>
      <div className="mx-auto max-w-[1160px] overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-shell-bg)] shadow-[var(--app-window-shadow)]">
        <div className="flex min-h-[560px]">
          <div className="w-[168px] shrink-0 bg-[var(--app-sidebar-bg)]">
            <WindowChrome />
            <AppSidebar />
          </div>

          <div className="relative w-px shrink-0">
            <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-[var(--app-divider)] to-transparent" />
            <div className="absolute inset-y-24 left-[-1px] w-[3px] rounded-full bg-gradient-to-b from-transparent via-[var(--app-divider-glow)] to-transparent" />
          </div>

          <main className="flex-1 bg-[var(--app-content-bg)]">
            <div className="flex h-16 items-center justify-between bg-[var(--app-surface)] px-7">
              <h1 className="text-[22px] font-bold text-[var(--app-title)]">{title}</h1>
              {headerRight ? <div>{headerRight}</div> : null}
            </div>
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}
