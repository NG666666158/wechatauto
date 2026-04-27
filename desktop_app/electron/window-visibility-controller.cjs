function attachWindowVisibilityGuards(mainWindow, options = {}) {
  const fallbackDelayMs = Number(options.fallbackDelayMs || 4000)
  const setTimer = options.setTimer || ((fn, timeoutMs) => setTimeout(fn, timeoutMs))
  const clearTimer = options.clearTimer || ((timerId) => clearTimeout(timerId))

  let shown = false
  let fallbackTimer = null

  const revealWindow = () => {
    if (shown) {
      return
    }
    shown = true
    if (fallbackTimer) {
      clearTimer(fallbackTimer)
      fallbackTimer = null
    }
    if (!mainWindow.isVisible || !mainWindow.isVisible()) {
      mainWindow.show()
    }
    if (typeof mainWindow.focus === "function") {
      mainWindow.focus()
    }
  }

  mainWindow.once("ready-to-show", revealWindow)
  if (mainWindow.webContents && typeof mainWindow.webContents.once === "function") {
    mainWindow.webContents.once("dom-ready", revealWindow)
    mainWindow.webContents.once("did-finish-load", revealWindow)
  }
  fallbackTimer = setTimer(revealWindow, fallbackDelayMs)

  return {
    revealWindow,
    dispose() {
      if (fallbackTimer) {
        clearTimer(fallbackTimer)
        fallbackTimer = null
      }
    },
  }
}

module.exports = {
  attachWindowVisibilityGuards,
}
