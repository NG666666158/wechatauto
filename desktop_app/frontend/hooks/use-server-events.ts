"use client"

import { useEffect, useRef } from "react"
import { createEventSource, parseServerEvent } from "@/lib/events"
import type { ServerEventEnvelope, ServerEventType } from "@/lib/events"

export function useServerEvents(
  handler: (event: ServerEventEnvelope) => void,
  options: { replay?: number; eventTypes?: ServerEventType[]; enabled?: boolean } = {},
) {
  const handlerRef = useRef(handler)
  const eventTypes = options.eventTypes ?? []
  const eventTypesKey = eventTypes.join("|")

  useEffect(() => {
    handlerRef.current = handler
  }, [handler])

  useEffect(() => {
    if (options.enabled === false) {
      return
    }
    const source = createEventSource({ replay: options.replay ?? 10 })
    const acceptedTypes = new Set(eventTypes)

    function handleMessage(event: MessageEvent<string>) {
      try {
        const parsed = parseServerEvent(event)
        if (acceptedTypes.size && !acceptedTypes.has(parsed.type as ServerEventType)) return
        handlerRef.current(parsed)
      } catch {
        // Ignore malformed event payloads; the next SSE message can still recover.
      }
    }

    source.onmessage = handleMessage
    for (const eventType of eventTypes) {
      source.addEventListener(eventType, handleMessage as EventListener)
    }

    return () => {
      source.close()
    }
  }, [options.enabled, options.replay, eventTypesKey])
}
