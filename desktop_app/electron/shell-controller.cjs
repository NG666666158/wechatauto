const {
  applyScheduleTickViaApi,
  getSettingsViaApi,
  getScheduleStatusViaApi,
  getTrayStateViaApi,
  pauseRuntimeViaApi,
  startRuntimeViaApi,
  stopRuntimeViaApi,
} = require("./backend-controller.cjs")

function normalizeShellPreferences(settings = {}) {
  return {
    runSilently: settings.run_silently !== false,
    escAction: normalizeEscAction(settings.esc_action),
  }
}

function normalizeEscAction(value) {
  const normalized = String(value || "pause").trim().toLowerCase()
  if (["pause", "stop", "hide", "quit", "exit"].includes(normalized)) {
    return normalized === "exit" ? "quit" : normalized
  }
  return "pause"
}

async function loadShellState(baseUrl, options = {}) {
  const [settings, trayState, scheduleStatus] = await Promise.all([
    getSettingsViaApi(baseUrl, options),
    getTrayStateViaApi(baseUrl, options),
    getScheduleStatusViaApi(baseUrl, options),
  ])
  return {
    settings,
    preferences: normalizeShellPreferences(settings),
    scheduleStatus,
    trayState,
  }
}

async function performShellAction(action, context) {
  const normalized = String(action || "").trim()
  if (!normalized) {
    return { ok: false, action: normalized }
  }

  if (normalized === "show_window") {
    context.showWindow()
    return { ok: true, action: normalized }
  }
  if (normalized === "hide_window") {
    context.hideWindow()
    return { ok: true, action: normalized }
  }
  if (normalized === "exit_app") {
    context.requestAppQuit()
    return { ok: true, action: normalized }
  }

  const baseUrl = context.baseUrl
  if (!baseUrl) {
    return { ok: false, action: normalized }
  }

  if (normalized === "start_daemon") {
    return { ok: await startRuntimeViaApi(baseUrl, context), action: normalized }
  }
  if (normalized === "pause_daemon") {
    return { ok: await pauseRuntimeViaApi(baseUrl, context), action: normalized }
  }
  if (normalized === "stop_daemon") {
    return { ok: await stopRuntimeViaApi(baseUrl, context), action: normalized }
  }

  return { ok: false, action: normalized }
}

async function handleEscAction(context) {
  const action = normalizeEscAction(context.escAction)

  if (action === "hide") {
    context.hideWindow()
    return { ok: true, action }
  }
  if (action === "quit") {
    context.requestAppQuit()
    return { ok: true, action }
  }
  if (action === "pause") {
    const result = await performShellAction("pause_daemon", context)
    if (context.runSilently) {
      context.hideWindow()
    }
    return { ...result, action }
  }
  if (action === "stop") {
    const result = await performShellAction("stop_daemon", context)
    if (context.runSilently) {
      context.hideWindow()
    }
    return { ...result, action }
  }

  context.hideWindow()
  return { ok: true, action: "hide" }
}

function buildTrayTemplate(trayState, context) {
  const items = Array.isArray(trayState.menu_items) ? trayState.menu_items : []
  return items.map((item) => ({
    id: String(item.item_id || item.action || ""),
    label: String(item.label || item.action || "Action"),
    enabled: item.enabled !== false,
    click: async () => {
      await performShellAction(String(item.action || ""), context)
      if (typeof context.refreshTray === "function") {
        await context.refreshTray()
      }
    },
  }))
}

async function runScheduleTick(context) {
  if (!context.baseUrl) {
    return { ok: false, action: "noop" }
  }
  const data = await applyScheduleTickViaApi(context.baseUrl, context)
  if (typeof context.refreshTray === "function") {
    await context.refreshTray()
  }
  return {
    ok: true,
    action: String(data.action || "noop"),
    data,
  }
}

module.exports = {
  buildTrayTemplate,
  handleEscAction,
  loadShellState,
  normalizeEscAction,
  normalizeShellPreferences,
  performShellAction,
  runScheduleTick,
}
