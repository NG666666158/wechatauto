function attachWindowDiagnostics(mainWindow, options = {}) {
  const logger = options.logger || console
  const emit = (eventType, payload = {}) => {
    if (typeof logger.info === "function") {
      logger.info(`[electron-shell] ${eventType}`, payload)
      return
    }
    if (typeof logger.log === "function") {
      logger.log(`[electron-shell] ${eventType}`, payload)
    }
  }

  if (mainWindow.webContents && typeof mainWindow.webContents.on === "function") {
    mainWindow.webContents.on("did-start-loading", () => emit("window.did_start_loading"))
    mainWindow.webContents.on("dom-ready", () => emit("window.dom_ready"))
    mainWindow.webContents.on("did-finish-load", () => emit("window.did_finish_load"))
    mainWindow.webContents.on("did-fail-load", (_event, code, description, validatedUrl, isMainFrame) => {
      emit("window.did_fail_load", {
        code,
        description,
        isMainFrame: Boolean(isMainFrame),
        validatedUrl,
      })
    })
    mainWindow.webContents.on("render-process-gone", (_event, details) => {
      emit("window.render_process_gone", details || {})
    })
  }
}

module.exports = {
  attachWindowDiagnostics,
}
