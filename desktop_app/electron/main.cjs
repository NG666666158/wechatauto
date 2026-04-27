const path = require("node:path")
const { app, BrowserWindow, ipcMain, Menu, Tray, nativeImage } = require("electron")

const { ensureBackendSession } = require("./backend-controller.cjs")
const { createWindowCloseHandler, shutdownDesktopShell } = require("./lifecycle-controller.cjs")
const { buildTrayTemplate, handleEscAction, loadShellState, runScheduleTick } = require("./shell-controller.cjs")
const { loadShellPreferences, saveShellPreferences, syncLaunchAtLogin } = require("./shell-preferences.cjs")
const { createShellPreferencesBridge } = require("./shell-preferences-bridge.cjs")
const { attachWindowDiagnostics } = require("./window-diagnostics.cjs")
const { attachWindowVisibilityGuards } = require("./window-visibility-controller.cjs")

const repoRoot = path.resolve(__dirname, "..", "..")
const frontendUrl = process.env.WECHAT_AI_FRONTEND_URL || "http://127.0.0.1:3000"

const shellState = {
  backendSession: null,
  mainWindow: null,
  tray: null,
  scheduleTimer: null,
  isQuitting: false,
  shutdownStarted: false,
  runSilently: true,
  escAction: "pause",
  scheduleEnabled: false,
  shellPreferences: null,
}

function createMainWindow() {
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  })

  mainWindow.webContents.on("before-input-event", async (_event, input) => {
    if (input.type === "keyDown" && input.key === "Escape") {
      await handleEscAction(buildShellContext())
    }
  })

  mainWindow.on(
    "close",
    createWindowCloseHandler({
      isQuitting: () => shellState.isQuitting,
      shouldHideOnClose: () => shellState.runSilently,
      hideWindow: () => mainWindow.hide(),
      requestAppQuit: () => app.quit(),
    }),
  )

  attachWindowDiagnostics(mainWindow)
  attachWindowVisibilityGuards(mainWindow)
  mainWindow.loadURL(frontendUrl)
  return mainWindow
}

async function syncShellPreferences() {
  if (!shellState.backendSession || !shellState.backendSession.baseUrl) {
    return
  }
  const shellData = await loadShellState(shellState.backendSession.baseUrl)
  shellState.scheduleEnabled = Boolean(shellData.settings && shellData.settings.schedule_enabled)
  shellState.runSilently = shellData.preferences.runSilently
  shellState.escAction = shellData.preferences.escAction
  await refreshTray(shellData.trayState)
  ensureScheduleTimer()
}

async function refreshTray(existingTrayState = null) {
  if (!shellState.backendSession || !shellState.backendSession.baseUrl) {
    return
  }
  const trayState = existingTrayState || (await loadShellState(shellState.backendSession.baseUrl)).trayState
  if (!shellState.tray) {
    shellState.tray = new Tray(nativeImage.createEmpty())
    shellState.tray.on("double-click", () => {
      if (shellState.mainWindow) {
        shellState.mainWindow.show()
        shellState.mainWindow.focus()
      }
    })
  }
  shellState.tray.setToolTip(String(trayState.tooltip || "WeChat AI"))
  shellState.tray.setContextMenu(Menu.buildFromTemplate(buildTrayTemplate(trayState, buildShellContext())))
}

function buildShellContext() {
  return {
    baseUrl: shellState.backendSession ? shellState.backendSession.baseUrl : "",
    runSilently: shellState.runSilently,
    escAction: shellState.escAction,
    showWindow: () => {
      if (shellState.mainWindow) {
        shellState.mainWindow.show()
        shellState.mainWindow.focus()
      }
    },
    hideWindow: () => {
      if (shellState.mainWindow) {
        shellState.mainWindow.hide()
      }
    },
    requestAppQuit: () => app.quit(),
    refreshTray: async () => {
      await syncShellPreferences()
    },
  }
}

function ensureScheduleTimer() {
  if (shellState.scheduleTimer) {
    clearInterval(shellState.scheduleTimer)
    shellState.scheduleTimer = null
  }
  const preferences = shellState.shellPreferences || { scheduleTickIntervalSeconds: 60 }
  if (!shellState.scheduleEnabled) {
    return
  }
  shellState.scheduleTimer = setInterval(async () => {
    try {
      await runScheduleTick(buildShellContext())
    } catch {
      // Ignore schedule tick failures in the shell loop and keep the app alive.
    }
  }, Math.max(Number(preferences.scheduleTickIntervalSeconds || 60), 15) * 1000)
}

app.whenReady().then(async () => {
  shellState.shellPreferences = loadShellPreferences(app.getPath("userData"))
  syncLaunchAtLogin(app, shellState.shellPreferences)
  const shellPreferencesBridge = createShellPreferencesBridge({
    appAdapter: app,
    baseDir: app.getPath("userData"),
    loadPreferences: loadShellPreferences,
    savePreferences: saveShellPreferences,
    syncLaunchAtLogin,
    onPreferencesChanged: (nextPreferences) => {
      shellState.shellPreferences = nextPreferences
      ensureScheduleTimer()
    },
  })
  ipcMain.handle("shell-preferences:get", () => shellPreferencesBridge.getPreferences())
  ipcMain.handle("shell-preferences:update", (_event, patch) => shellPreferencesBridge.updatePreferences(patch))
  shellState.backendSession = await ensureBackendSession({
    repoRoot,
    host: "127.0.0.1",
    port: 8765,
    startupTimeoutMs: 30000,
    pollIntervalMs: 1000,
  })
  shellState.mainWindow = createMainWindow()
  await syncShellPreferences()
})

app.on("activate", () => {
  if (shellState.mainWindow) {
    shellState.mainWindow.show()
    return
  }
  shellState.mainWindow = createMainWindow()
})

app.on("window-all-closed", (event) => {
  if (process.platform === "darwin") {
    return
  }
  event.preventDefault()
})

app.on("before-quit", async (event) => {
  if (shellState.shutdownStarted) {
    return
  }
  shellState.shutdownStarted = true
  shellState.isQuitting = true
  event.preventDefault()
  try {
    await shutdownDesktopShell({
      backendSession: shellState.backendSession,
    })
  } finally {
    if (shellState.scheduleTimer) {
      clearInterval(shellState.scheduleTimer)
      shellState.scheduleTimer = null
    }
    if (shellState.tray) {
      shellState.tray.destroy()
      shellState.tray = null
    }
    app.exit(0)
  }
})
