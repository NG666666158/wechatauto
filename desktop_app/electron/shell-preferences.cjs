const fs = require("node:fs")
const path = require("node:path")

const DEFAULT_PREFERENCES = {
  launchAtLogin: false,
  scheduleTickIntervalSeconds: 60,
}

function resolvePreferencesPath(baseDir) {
  return path.join(baseDir, "shell-preferences.json")
}

function loadShellPreferences(baseDir) {
  const preferencesPath = resolvePreferencesPath(baseDir)
  if (!fs.existsSync(preferencesPath)) {
    return { ...DEFAULT_PREFERENCES }
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(preferencesPath, "utf8"))
    return normalizePreferences(parsed)
  } catch {
    return { ...DEFAULT_PREFERENCES }
  }
}

function saveShellPreferences(baseDir, patch = {}) {
  const preferencesPath = resolvePreferencesPath(baseDir)
  const nextValue = {
    ...loadShellPreferences(baseDir),
    ...patch,
  }
  const normalized = normalizePreferences(nextValue)
  fs.mkdirSync(baseDir, { recursive: true })
  fs.writeFileSync(preferencesPath, JSON.stringify(normalized, null, 2), "utf8")
  return normalized
}

function normalizePreferences(value = {}) {
  const interval = Number(value.scheduleTickIntervalSeconds || DEFAULT_PREFERENCES.scheduleTickIntervalSeconds)
  return {
    launchAtLogin: Boolean(value.launchAtLogin),
    scheduleTickIntervalSeconds: Number.isFinite(interval) ? Math.min(Math.max(Math.round(interval), 15), 3600) : 60,
  }
}

function syncLaunchAtLogin(appAdapter, preferences) {
  if (!appAdapter || typeof appAdapter.setLoginItemSettings !== "function") {
    return false
  }
  appAdapter.setLoginItemSettings({
    openAtLogin: Boolean(preferences.launchAtLogin),
  })
  return true
}

module.exports = {
  DEFAULT_PREFERENCES,
  loadShellPreferences,
  normalizePreferences,
  resolvePreferencesPath,
  saveShellPreferences,
  syncLaunchAtLogin,
}
