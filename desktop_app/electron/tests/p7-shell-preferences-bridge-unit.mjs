import assert from "node:assert/strict"
import { createRequire } from "node:module"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const require = createRequire(import.meta.url)
const __dirname = dirname(fileURLToPath(import.meta.url))

const { createShellPreferencesBridge } = require(join(__dirname, "..", "shell-preferences-bridge.cjs"))

testBridgeReturnsCurrentPreferences()
testBridgePersistsPatchAndRunsSideEffects()

console.log("P7 shell preferences bridge unit tests passed")

function testBridgeReturnsCurrentPreferences() {
  const bridge = createShellPreferencesBridge({
    loadPreferences: () => ({ launchAtLogin: true, scheduleTickIntervalSeconds: 120 }),
    savePreferences: () => {
      throw new Error("should not save during get")
    },
    syncLaunchAtLogin: () => {
      throw new Error("should not sync during get")
    },
    onPreferencesChanged: () => {
      throw new Error("should not notify during get")
    },
  })

  assert.deepEqual(bridge.getPreferences(), {
    launchAtLogin: true,
    scheduleTickIntervalSeconds: 120,
  })
}

function testBridgePersistsPatchAndRunsSideEffects() {
  const calls = []
  const bridge = createShellPreferencesBridge({
    loadPreferences: () => ({ launchAtLogin: false, scheduleTickIntervalSeconds: 60 }),
    savePreferences: (_baseDir, patch) => {
      calls.push(["save", patch])
      return {
        launchAtLogin: true,
        scheduleTickIntervalSeconds: 300,
      }
    },
    syncLaunchAtLogin: (_appAdapter, preferences) => {
      calls.push(["sync", preferences])
      return true
    },
    onPreferencesChanged: (preferences) => {
      calls.push(["changed", preferences])
    },
  })

  const updated = bridge.updatePreferences({
    launchAtLogin: true,
    scheduleTickIntervalSeconds: 301,
  })

  assert.deepEqual(updated, {
    launchAtLogin: true,
    scheduleTickIntervalSeconds: 300,
  })
  assert.deepEqual(calls, [
    ["save", { launchAtLogin: true, scheduleTickIntervalSeconds: 301 }],
    ["sync", { launchAtLogin: true, scheduleTickIntervalSeconds: 300 }],
    ["changed", { launchAtLogin: true, scheduleTickIntervalSeconds: 300 }],
  ])
}
