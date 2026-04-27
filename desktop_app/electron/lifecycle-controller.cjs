const { shutdownManagedBackend, stopRuntimeViaApi } = require("./backend-controller.cjs")

function createWindowCloseHandler(options) {
  const isQuitting = options.isQuitting
  const shouldHideOnClose = options.shouldHideOnClose
  const hideWindow = options.hideWindow
  const requestAppQuit = options.requestAppQuit

  return function handleWindowClose(event) {
    if (isQuitting()) {
      return
    }
    event.preventDefault()
    if (shouldHideOnClose()) {
      hideWindow()
      return
    }
    requestAppQuit()
  }
}

async function shutdownDesktopShell(options) {
  const backendSession = options.backendSession || null
  const stopRuntime = options.stopRuntime || stopRuntimeViaApi
  const stopManaged = options.stopManagedBackend || shutdownManagedBackend

  let runtimeStopped = false
  let backendStopped = false

  if (backendSession && backendSession.baseUrl) {
    runtimeStopped = await stopRuntime(backendSession.baseUrl, options)
  }
  if (backendSession && backendSession.managed) {
    backendStopped = await stopManaged(backendSession)
  }

  return {
    runtimeStopped,
    backendStopped,
  }
}

module.exports = {
  createWindowCloseHandler,
  shutdownDesktopShell,
}
