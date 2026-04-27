"use client"

import { useEffect, useRef, useState } from "react"
import { useServerEvents } from "@/hooks/use-server-events"
import { toast } from "@/hooks/use-toast"

const MAX_SEEN_EVENT_IDS = 100
const SEEN_EVENT_IDS_STORAGE_KEY = "wechat-ai-global-seen-event-ids"

export function GlobalEventListener() {
  const seenEventIdsRef = useRef<string[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    seenEventIdsRef.current = loadSeenEventIds()
    setReady(true)
  }, [])

  useServerEvents((event) => {
    if (hasSeenEvent(seenEventIdsRef.current, event.id)) {
      return
    }
    rememberEventId(seenEventIdsRef.current, event.id)

    if (event.type === "message.received") {
      const sender = stringify(event.data.sender) || "新消息"
      const text = stringify(event.data.text) || "收到一条新消息"
      toast({
        title: `收到新消息 · ${sender}`,
        description: truncate(text, 72),
      })
      return
    }

    if (event.type === "error") {
      const title = stringify(event.data.code) || "运行异常"
      const description = stringify(event.data.message) || "出现了一条新的错误事件"
      toast({
        title,
        description: truncate(description, 96),
        variant: "destructive",
      })
      return
    }

    if (event.type !== "log.event") {
      return
    }

    const logEventType = stringify(event.data.event_type)
    const logLevel = stringify(event.data.level).toLowerCase()
    const message = stringify(event.data.message) || stringify(event.data.exception_message) || stringify(event.data.reason)

    if (logEventType === "window.environment.changed") {
      toast({
        title: "微信窗口状态变化",
        description: truncate(message || "窗口环境发生变化", 96),
      })
      return
    }

    if (logEventType === "active_anchor_missed") {
      toast({
        title: "消息锚点丢失",
        description: truncate(message || "检测到活动会话锚点需要重新对齐", 96),
      })
      return
    }

    if (logLevel === "error" || logEventType === "loop_error") {
      toast({
        title: logEventType || "运行异常",
        description: truncate(message || "运行时产生新的错误日志", 96),
        variant: "destructive",
      })
    }
  }, { eventTypes: ["message.received", "log.event", "error"], replay: 1, enabled: ready })

  return null
}

function hasSeenEvent(buffer: string[], id: string) {
  return Boolean(id) && buffer.includes(id)
}

function rememberEventId(buffer: string[], id: string) {
  if (!id) {
    return
  }
  buffer.push(id)
  if (buffer.length > MAX_SEEN_EVENT_IDS) {
    buffer.splice(0, buffer.length - MAX_SEEN_EVENT_IDS)
  }
  persistSeenEventIds(buffer)
}

function loadSeenEventIds() {
  if (typeof window === "undefined") {
    return []
  }
  try {
    const raw = window.sessionStorage.getItem(SEEN_EVENT_IDS_STORAGE_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : []
  } catch {
    return []
  }
}

function persistSeenEventIds(ids: string[]) {
  if (typeof window === "undefined") {
    return
  }
  try {
    window.sessionStorage.setItem(SEEN_EVENT_IDS_STORAGE_KEY, JSON.stringify(ids))
  } catch {
    // Ignore storage failures and fall back to in-memory dedupe for this session.
  }
}

function stringify(value: unknown) {
  return typeof value === "string" ? value.trim() : ""
}

function truncate(value: string, maxChars: number) {
  if (value.length <= maxChars) {
    return value
  }
  return `${value.slice(0, maxChars).trimEnd()}...`
}
