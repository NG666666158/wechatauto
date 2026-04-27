import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { join } from "node:path"

const root = fileURLToPath(new URL("..", import.meta.url))

const checks = [
  {
    name: "five primary pages exist",
    run: () =>
      [
        "app/page.tsx",
        "app/messages/page.tsx",
        "app/customers/page.tsx",
        "app/knowledge/page.tsx",
        "app/settings/page.tsx",
      ].every((file) => existsSync(join(root, file))),
  },
  {
    name: "sidebar exposes knowledge between customers and settings",
    run: () => {
      const source = read("components/app-sidebar.tsx")
      const customers = source.indexOf('href: "/customers"')
      const knowledge = source.indexOf('href: "/knowledge"')
      const settings = source.indexOf('href: "/settings"')
      return customers > -1 && knowledge > customers && settings > knowledge
    },
  },
  {
    name: "api client covers dashboard settings messages customers knowledge",
    run: () => {
      const source = read("lib/api.ts")
      return [
        "getDashboardSummary",
        "getSettings",
        "listConversations",
        "sendConversationReply",
        "listCustomers",
        "updateGlobalSelfIdentity",
        "getKnowledgeStatus",
        "searchKnowledge",
        "importKnowledgeFiles",
        "buildWebKnowledgeFromDocuments",
      ].every((token) => source.includes(token))
    },
  },
  {
    name: "pages render backend-offline error states",
    run: () =>
      ["app/page.tsx", "app/messages/page.tsx", "app/customers/page.tsx", "app/knowledge/page.tsx", "app/settings/page.tsx"]
        .every((file) => read(file).includes("ErrorState")),
  },
  {
    name: "dangerous message send requires confirmation",
    run: () => read("app/messages/page.tsx").includes("window.confirm"),
  },
  {
    name: "knowledge page supports local import and web build actions",
    run: () => {
      const source = read("app/knowledge/page.tsx")
      return source.includes("importKnowledgeFiles") && source.includes("buildWebKnowledgeFromDocuments")
    },
  },
  {
    name: "home page preflights environment before real auto reply start",
    run: () => {
      const source = read("app/page.tsx")
      return (
        source.includes("bootstrapCheckRuntime") &&
        source.includes("bootstrapStartRuntime") &&
        read("lib/api.ts").includes('"/runtime/bootstrap-start"') &&
        read("lib/api.ts").includes("BOOTSTRAP_READY_TIMEOUT_SECONDS = 120") &&
        source.includes("result.data.bootstrap?.ui_ready") &&
        source.indexOf("bootstrapCheckRuntime") < source.indexOf("bootstrapStartRuntime") &&
        !source.includes("apiClient.getWechatEnvironment(),")
      )
    },
  },
  {
    name: "settings page exposes desktop shell preferences",
    run: () => {
      const source = read("app/settings/page.tsx")
      const shellSource = read("lib/electron-shell.ts")
      return (
        source.includes("开机自启") &&
        source.includes("定时巡检间隔") &&
        source.includes("launchAtLogin") &&
        source.includes("scheduleTickIntervalSeconds") &&
        shellSource.includes("getDesktopShellBridge") &&
        shellSource.includes("updatePreferences")
      )
    },
  },
]

const failures = checks.filter((check) => !check.run())

if (failures.length) {
  console.error("P5 frontend acceptance failed:")
  for (const failure of failures) {
    console.error(`- ${failure.name}`)
  }
  process.exit(1)
}

console.log(`P5 frontend acceptance passed: ${checks.length}/${checks.length} checks`)

function read(file) {
  return readFileSync(join(root, file), "utf8")
}
