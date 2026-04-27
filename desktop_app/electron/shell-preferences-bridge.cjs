function createShellPreferencesBridge(options = {}) {
  const baseDir = options.baseDir || ""
  const appAdapter = options.appAdapter || null
  const loadPreferences = options.loadPreferences
  const savePreferences = options.savePreferences
  const syncLaunchAtLogin = options.syncLaunchAtLogin
  const onPreferencesChanged = options.onPreferencesChanged || (() => {})

  if (typeof loadPreferences !== "function" || typeof savePreferences !== "function") {
    throw new Error("Shell preferences bridge requires loadPreferences and savePreferences functions")
  }

  return {
    getPreferences() {
      return loadPreferences(baseDir)
    },
    updatePreferences(patch = {}) {
      const nextPreferences = savePreferences(baseDir, patch)
      if (typeof syncLaunchAtLogin === "function") {
        syncLaunchAtLogin(appAdapter, nextPreferences)
      }
      onPreferencesChanged(nextPreferences)
      return nextPreferences
    },
  }
}

module.exports = {
  createShellPreferencesBridge,
}
