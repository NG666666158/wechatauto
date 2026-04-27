export type ServerEventType =
  | "runtime.status"
  | "message.received"
  | "message.sent"
  | "knowledge.progress"
  | "log.event"
  | "error"

export type ServerEventEnvelope<TData = Record<string, unknown>> = {
  id: string
  type: ServerEventType | string
  timestamp: string
  data: TData
  trace_id: string
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_WECHAT_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8765/api/v1"

export function buildEventsUrl(options: { replay?: number } = {}) {
  const url = new URL(`${API_BASE_URL}/events`)
  if (options.replay !== undefined) {
    url.searchParams.set("replay", String(options.replay))
  }
  return url.toString()
}

export function createEventSource(options: { replay?: number } = {}) {
  return new EventSource(buildEventsUrl(options))
}

export function parseServerEvent<TData = Record<string, unknown>>(event: MessageEvent<string>) {
  return JSON.parse(event.data) as ServerEventEnvelope<TData>
}
