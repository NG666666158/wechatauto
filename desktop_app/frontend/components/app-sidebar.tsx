"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, MessageSquare, Settings, User } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "\u9996\u9875", href: "/", icon: Home },
  { label: "\u6d88\u606f", href: "/messages", icon: MessageSquare },
  { label: "\u5ba2\u6237", href: "/customers", icon: User },
  { label: "\u8bbe\u7f6e", href: "/settings", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-[168px] shrink-0 bg-[var(--app-sidebar-bg)] px-3 py-2">
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-3 text-[17px] transition-colors",
                active
                  ? "bg-[var(--app-nav-active-bg)] font-bold text-[var(--app-nav-active-text)]"
                  : "font-semibold text-[var(--app-nav-text)] hover:bg-[var(--app-nav-hover-bg)]",
              )}
            >
              <Icon className="h-6 w-6" strokeWidth={active ? 2.4 : 1.9} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
