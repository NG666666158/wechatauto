import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import { createRequire } from "node:module"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const require = createRequire(import.meta.url)
const __dirname = dirname(fileURLToPath(import.meta.url))

const backend = require(join(__dirname, "..", "backend-controller.cjs"))
const lifecycle = require(join(__dirname, "..", "lifecycle-controller.cjs"))
const shell = require(join(__dirname, "..", "shell-controller.cjs"))
const preferences = require(join(__dirname, "..", "shell-preferences.cjs"))
const visibility = require(join(__dirname, "..", "window-visibility-controller.cjs"))
const diagnostics = require(join(__dirname, "..", "window-diagnostics.cjs"))

await testReuseExistingBackend()
await testSpawnManagedBackendUntilHealthy()
await testShutdownStopsRuntimeAndManagedBackend()
testWindowCloseHidesWithoutQuitting()
await testLoadShellStateNormalizesPreferences()
await testEscActionPauseHidesWhenSilent()
await testTrayTemplateDispatchesActionAndRefreshes()
await testRunScheduleTickRefreshesTray()
testShellPreferencesPersistAndSyncLaunchAtLogin()
testWindowVisibilityShowsOnDidFinishLoad()
testWindowVisibilityFallbackShowsWindow()
testWindowDiagnosticsCapturesLoadFailure()

console.log("P7 shell unit tests passed")

async function testReuseExistingBackend() {
  let spawnCalled = false
  const session = await backend.ensureBackendSession({
    baseUrl: "http://127.0.0.1:8765",
    requestJson: async () => ({ statusCode: 200, data: { success: true } }),
    spawnFn: () => {
      spawnCalled = true
      return null
    },
  })

  assert.equal(session.reused, true)
  assert.equal(session.managed, false)
  assert.equal(spawnCalled, false)
}

async function testSpawnManagedBackendUntilHealthy() {
  const probes = [
    { statusCode: 500, data: null },
    { statusCode: 500, data: null },
    { statusCode: 200, data: { success: true } },
  ]
  let spawnCalled = 0
  const child = {
    killed: false,
    kill() {
      this.killed = true
    },
  }

  const session = await backend.ensureBackendSession({
    baseUrl: "http://127.0.0.1:8765",
    requestJson: async () => probes.shift() ?? { statusCode: 200, data: { success: true } },
    spawnFn: () => {
      spawnCalled += 1
      return child
    },
    pollIntervalMs: 1,
    startupTimeoutMs: 100,
  })

  assert.equal(spawnCalled, 1)
  assert.equal(session.managed, true)
  assert.equal(session.reused, false)
  assert.equal(session.child, child)
}

async function testShutdownStopsRuntimeAndManagedBackend() {
  const calls = []
  const child = {
    killed: false,
    kill() {
      this.killed = true
      calls.push("kill")
    },
  }
  const result = await lifecycle.shutdownDesktopShell({
    backendSession: {
      baseUrl: "http://127.0.0.1:8765",
      managed: true,
      child,
    },
    stopRuntime: async (baseUrl) => {
      calls.push(`runtime:${baseUrl}`)
      return true
    },
    stopManagedBackend: async (session) => {
      calls.push(`backend:${session.baseUrl}`)
      return true
    },
  })

  assert.deepEqual(calls, ["runtime:http://127.0.0.1:8765", "backend:http://127.0.0.1:8765"])
  assert.deepEqual(result, {
    runtimeStopped: true,
    backendStopped: true,
  })
}

function testWindowCloseHidesWithoutQuitting() {
  const calls = []
  const handler = lifecycle.createWindowCloseHandler({
    isQuitting: () => false,
    shouldHideOnClose: () => true,
    hideWindow: () => calls.push("hide"),
    requestAppQuit: () => calls.push("quit"),
  })

  handler({
    preventDefault() {
      calls.push("prevent")
    },
  })

  assert.deepEqual(calls, ["prevent", "hide"])
}

async function testLoadShellStateNormalizesPreferences() {
  const responses = new Map([
    ["http://127.0.0.1:8765/api/v1/settings", { statusCode: 200, data: { data: { run_silently: false, esc_action: "stop" } } }],
    ["http://127.0.0.1:8765/api/v1/shell/tray-state", { statusCode: 200, data: { data: { tooltip: "WeChat AI", menu_items: [] } } }],
  ])

  const state = await shell.loadShellState("http://127.0.0.1:8765", {
    requestJson: async (url) => responses.get(url),
  })

  assert.deepEqual(state.preferences, {
    runSilently: false,
    escAction: "stop",
  })
  assert.equal(state.trayState.tooltip, "WeChat AI")
  assert.equal(state.scheduleStatus.enabled, false)
  assert.equal(state.scheduleStatus.reason, "unavailable")
}

async function testEscActionPauseHidesWhenSilent() {
  const calls = []
  const result = await shell.handleEscAction({
    baseUrl: "http://127.0.0.1:8765",
    escAction: "pause",
    runSilently: true,
    requestJson: async (url) => {
      calls.push(url)
      return { statusCode: 200, data: { success: true } }
    },
    hideWindow: () => calls.push("hide"),
    requestAppQuit: () => calls.push("quit"),
    showWindow: () => calls.push("show"),
  })

  assert.equal(result.ok, true)
  assert.equal(result.action, "pause")
  assert.deepEqual(calls, ["http://127.0.0.1:8765/api/v1/runtime/pause", "hide"])
}

async function testTrayTemplateDispatchesActionAndRefreshes() {
  const calls = []
  const template = shell.buildTrayTemplate(
    {
      menu_items: [
        { item_id: "start", label: "开始守护", action: "start_daemon", enabled: true },
      ],
    },
    {
      baseUrl: "http://127.0.0.1:8765",
      requestJson: async (url) => {
        calls.push(url)
        return { statusCode: 200, data: { success: true } }
      },
      showWindow: () => calls.push("show"),
      hideWindow: () => calls.push("hide"),
      requestAppQuit: () => calls.push("quit"),
      refreshTray: async () => calls.push("refresh"),
    },
  )

  assert.equal(template.length, 1)
  assert.equal(template[0].label, "开始守护")
  await template[0].click()
  assert.deepEqual(calls, ["http://127.0.0.1:8765/api/v1/runtime/bootstrap-start", "refresh"])
}

async function testRunScheduleTickRefreshesTray() {
  const calls = []
  const result = await shell.runScheduleTick({
    baseUrl: "http://127.0.0.1:8765",
    requestJson: async (url) => {
      calls.push(url)
      return {
        statusCode: 200,
        data: {
          data: {
            action: "pause",
            daemon: { state: "paused" },
          },
        },
      }
    },
    refreshTray: async () => calls.push("refresh"),
  })

  assert.equal(result.ok, true)
  assert.equal(result.action, "pause")
  assert.deepEqual(calls, ["http://127.0.0.1:8765/api/v1/shell/schedule/tick", "refresh"])
}

function testShellPreferencesPersistAndSyncLaunchAtLogin() {
  const tempBaseDir = fs.mkdtempSync(join(os.tmpdir(), "wechat-ai-shell-"))
  const saved = preferences.saveShellPreferences(tempBaseDir, {
    launchAtLogin: true,
    scheduleTickIntervalSeconds: 5,
  })
  const loaded = preferences.loadShellPreferences(tempBaseDir)
  const calls = []
  const appAdapter = {
    setLoginItemSettings(payload) {
      calls.push(payload)
    },
  }

  assert.equal(saved.launchAtLogin, true)
  assert.equal(saved.scheduleTickIntervalSeconds, 15)
  assert.deepEqual(loaded, saved)
  assert.equal(preferences.syncLaunchAtLogin(appAdapter, loaded), true)
  assert.deepEqual(calls, [{ openAtLogin: true }])
}

function testWindowVisibilityShowsOnDidFinishLoad() {
  const events = new Map()
  const webEvents = new Map()
  const calls = []
  const timerCalls = []
  const mainWindow = {
    once(event, handler) {
      events.set(event, handler)
    },
    show() {
      calls.push("show")
    },
    focus() {
      calls.push("focus")
    },
    isVisible() {
      return false
    },
    webContents: {
      once(event, handler) {
        webEvents.set(event, handler)
      },
    },
  }

  visibility.attachWindowVisibilityGuards(mainWindow, {
    fallbackDelayMs: 3000,
    setTimer(fn, timeoutMs) {
      timerCalls.push(timeoutMs)
      return { fn, timeoutMs }
    },
    clearTimer() {},
  })

  webEvents.get("did-finish-load")()

  assert.deepEqual(calls, ["show", "focus"])
  assert.deepEqual(timerCalls, [3000])
}

function testWindowVisibilityFallbackShowsWindow() {
  const calls = []
  let fallback = null
  const mainWindow = {
    once() {},
    show() {
      calls.push("show")
    },
    focus() {
      calls.push("focus")
    },
    isVisible() {
      return false
    },
    webContents: {
      once() {},
    },
  }

  visibility.attachWindowVisibilityGuards(mainWindow, {
    fallbackDelayMs: 1500,
    setTimer(fn) {
      fallback = fn
      return { id: "timer" }
    },
    clearTimer() {},
  })

  fallback()

  assert.deepEqual(calls, ["show", "focus"])
}

function testWindowDiagnosticsCapturesLoadFailure() {
  const webEvents = new Map()
  const logs = []
  const mainWindow = {
    webContents: {
      on(event, handler) {
        webEvents.set(event, handler)
      },
    },
  }

  diagnostics.attachWindowDiagnostics(mainWindow, {
    logger: {
      info(message, payload) {
        logs.push([message, payload])
      },
    },
  })

  webEvents.get("did-fail-load")({}, -102, "ERR_CONNECTION_REFUSED", "http://127.0.0.1:3000/settings", true)

  assert.deepEqual(logs, [
    [
      "[electron-shell] window.did_fail_load",
      {
        code: -102,
        description: "ERR_CONNECTION_REFUSED",
        isMainFrame: true,
        validatedUrl: "http://127.0.0.1:3000/settings",
      },
    ],
  ])
}
