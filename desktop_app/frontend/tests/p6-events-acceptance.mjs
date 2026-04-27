import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { join } from "node:path"

const frontendRoot = fileURLToPath(new URL("..", import.meta.url))
const repoRoot = join(frontendRoot, "..", "..")

const checks = [
  {
    name: "frontend event client exists",
    run: () => existsSync(join(frontendRoot, "lib", "events.ts")),
  },
  {
    name: "frontend event client builds /events url and EventSource",
    run: () => {
      const source = read(frontendRoot, "lib/events.ts")
      return source.includes("/events") && source.includes("new EventSource") && source.includes("parseServerEvent")
    },
  },
  {
    name: "frontend pages subscribe to server events",
    run: () => {
      const hookExists = existsSync(join(frontendRoot, "hooks", "use-server-events.ts"))
      const home = read(frontendRoot, "app/page.tsx")
      const messages = read(frontendRoot, "app/messages/page.tsx")
      const knowledge = read(frontendRoot, "app/knowledge/page.tsx")
      return hookExists && [home, messages, knowledge].every((source) => source.includes("useServerEvents"))
    },
  },
  {
    name: "frontend layout includes global event notifications",
    run: () => {
      const layout = read(frontendRoot, "app/layout.tsx")
      const listener = read(frontendRoot, "components/global-event-listener.tsx")
      return (
        layout.includes("GlobalEventListener") &&
        layout.includes("Toaster") &&
        listener.includes("useServerEvents") &&
        listener.includes("toast(") &&
        listener.includes("sessionStorage")
      )
    },
  },
  {
    name: "global notifications surface loop_error exception details",
    run: () => {
      const listener = read(frontendRoot, "components/global-event-listener.tsx")
      return (
        listener.includes("exception_message") &&
        listener.includes('logEventType === "loop_error"') &&
        listener.includes('variant: "destructive"')
      )
    },
  },
  {
    name: "backend exposes SSE events router",
    run: () => {
      const source = read(repoRoot, "wechat_ai/server/api/events.py")
      return (
        source.includes("StreamingResponse") &&
        source.includes("text/event-stream") &&
        source.includes("once") &&
        source.includes("next_event") &&
        !source.includes("relay.sync(")
      )
    },
  },
  {
    name: "backend publishes runtime, message, control, and knowledge events",
    run: () => {
      const runtime = read(repoRoot, "wechat_ai/server/api/runtime.py")
      const conversations = read(repoRoot, "wechat_ai/server/api/conversations.py")
      const controls = read(repoRoot, "wechat_ai/server/api/controls.py")
      const knowledge = read(repoRoot, "wechat_ai/server/api/knowledge.py")
      return (
        runtime.includes("runtime.status") &&
        conversations.includes("message.sent") &&
        controls.includes("log.event") &&
        knowledge.includes("knowledge.progress")
      )
    },
  },
  {
    name: "api snapshot includes /api/v1/events",
    run: () => read(repoRoot, "docs/api-contract/api-contract.baseline.json").includes("/api/v1/events"),
  },
]

const failures = checks.filter((check) => !check.run())

if (failures.length) {
  console.error("P6 events acceptance failed:")
  for (const failure of failures) {
    console.error(`- ${failure.name}`)
  }
  process.exit(1)
}

console.log(`P6 events acceptance passed: ${checks.length}/${checks.length} checks`)

function read(root, file) {
  return readFileSync(join(root, file), "utf8")
}
