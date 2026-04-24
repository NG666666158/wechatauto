import { cn } from "@/lib/utils"

const palette = [
  "bg-gradient-to-br from-blue-400 to-blue-500",
  "bg-gradient-to-br from-pink-400 to-rose-400",
  "bg-gradient-to-br from-emerald-400 to-teal-500",
  "bg-gradient-to-br from-amber-400 to-orange-500",
  "bg-gradient-to-br from-violet-400 to-indigo-500",
  "bg-gradient-to-br from-sky-400 to-cyan-500",
]

interface UserAvatarProps {
  name: string
  size?: number
  className?: string
}

export function UserAvatar({ name, size = 40, className }: UserAvatarProps) {
  const idx = name.charCodeAt(0) % palette.length
  const initial = name.slice(-1)
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full text-white font-medium",
        palette[idx],
        className,
      )}
      style={{ width: size, height: size, fontSize: size * 0.42 }}
      aria-hidden
    >
      {initial}
    </div>
  )
}
