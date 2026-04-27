const http = require("node:http")
const https = require("node:https")
const { spawn } = require("node:child_process")

function buildBackendBaseUrl(options = {}) {
  const host = String(options.host || "127.0.0.1")
  const port = Number(options.port || 8765)
  return `http://${host}:${port}`
}

function buildApiUrl(baseUrl, path) {
  return `${String(baseUrl).replace(/\/$/, "")}${path}`
}

function requestJson(url, options = {}) {
  const timeoutMs = Number(options.timeoutMs || 3000)
  const body = options.body === undefined ? undefined : JSON.stringify(options.body)
  const target = new URL(url)
  const transport = target.protocol === "https:" ? https : http

  return new Promise((resolve, reject) => {
    const request = transport.request(
      target,
      {
        method: options.method || "GET",
        headers: {
          "content-type": "application/json",
          ...(body ? { "content-length": Buffer.byteLength(body) } : {}),
          ...(options.headers || {}),
        },
      },
      (response) => {
        const chunks = []
        response.on("data", (chunk) => chunks.push(chunk))
        response.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8")
          let data = null
          if (raw.trim()) {
            try {
              data = JSON.parse(raw)
            } catch (error) {
              reject(error)
              return
            }
          }
          resolve({
            statusCode: response.statusCode || 0,
            data,
          })
        })
      },
    )

    request.on("error", reject)
    request.setTimeout(timeoutMs, () => {
      request.destroy(new Error(`Request timed out after ${timeoutMs}ms`))
    })

    if (body) {
      request.write(body)
    }
    request.end()
  })
}

function unwrapApiData(response, fallback) {
  if (response && response.data && response.data.data !== undefined) {
    return response.data.data
  }
  return fallback
}

async function probeBackend(baseUrl, options = {}) {
  try {
    const response = await (options.requestJson || requestJson)(buildApiUrl(baseUrl, "/api/v1/health"), {
      method: "GET",
      timeoutMs: options.timeoutMs || 3000,
    })
    return response.statusCode === 200 && Boolean(response.data && response.data.success)
  } catch {
    return false
  }
}

function spawnBackendProcess(options = {}) {
  const repoRoot = options.repoRoot
  const host = String(options.host || "127.0.0.1")
  const port = Number(options.port || 8765)
  const pythonCommand = Array.isArray(options.pythonCommand) && options.pythonCommand.length
    ? options.pythonCommand
    : ["py", "-3"]
  const [command, ...commandArgs] = pythonCommand
  const args = [
    ...commandArgs,
    "-m",
    "uvicorn",
    "wechat_ai.server.main:app",
    "--host",
    host,
    "--port",
    String(port),
  ]

  return (options.spawnFn || spawn)(command, args, {
    cwd: repoRoot,
    windowsHide: true,
    stdio: "ignore",
  })
}

async function ensureBackendSession(options = {}) {
  const baseUrl = options.baseUrl || buildBackendBaseUrl(options)
  const request = options.requestJson || requestJson
  if (await probeBackend(baseUrl, { requestJson: request, timeoutMs: options.probeTimeoutMs || 3000 })) {
    return {
      baseUrl,
      managed: false,
      reused: true,
      child: null,
    }
  }

  const child = spawnBackendProcess(options)
  const startupTimeoutMs = Number(options.startupTimeoutMs || 30000)
  const pollIntervalMs = Number(options.pollIntervalMs || 1000)
  const deadline = Date.now() + startupTimeoutMs

  while (Date.now() < deadline) {
    if (await probeBackend(baseUrl, { requestJson: request, timeoutMs: options.probeTimeoutMs || 3000 })) {
      return {
        baseUrl,
        managed: true,
        reused: false,
        child,
      }
    }
    await sleep(pollIntervalMs)
  }

  if (child && !child.killed && typeof child.kill === "function") {
    child.kill()
  }
  throw new Error(`Backend did not become healthy within ${startupTimeoutMs}ms`)
}

async function stopRuntimeViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  try {
    const response = await request(buildApiUrl(baseUrl, "/api/v1/runtime/stop"), {
      method: "POST",
      timeoutMs: options.timeoutMs || 5000,
    })
    if (response.statusCode === 200 || response.statusCode === 409) {
      return true
    }
    return false
  } catch {
    return false
  }
}

async function pauseRuntimeViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  try {
    const response = await request(buildApiUrl(baseUrl, "/api/v1/runtime/pause"), {
      method: "POST",
      timeoutMs: options.timeoutMs || 5000,
    })
    if (response.statusCode === 200 || response.statusCode === 409) {
      return true
    }
    return false
  } catch {
    return false
  }
}

async function startRuntimeViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  try {
    const response = await request(buildApiUrl(baseUrl, "/api/v1/runtime/bootstrap-start"), {
      method: "POST",
      timeoutMs: options.timeoutMs || 45000,
      body: {
        mode: "global",
        ready_timeout_seconds: 20,
        poll_interval_seconds: 1,
        narrator_settle_seconds: 10,
        wait_for_ui_ready_before_guardian: true,
      },
    })
    return response.statusCode === 200
  } catch {
    return false
  }
}

async function getSettingsViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  const response = await request(buildApiUrl(baseUrl, "/api/v1/settings"), {
    method: "GET",
    timeoutMs: options.timeoutMs || 5000,
  })
  return unwrapApiData(response, {})
}

async function getTrayStateViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  const response = await request(buildApiUrl(baseUrl, "/api/v1/shell/tray-state"), {
    method: "GET",
    timeoutMs: options.timeoutMs || 5000,
  })
  return unwrapApiData(response, { tooltip: "WeChat AI", menu_items: [] })
}

async function getScheduleStatusViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  const response = await request(buildApiUrl(baseUrl, "/api/v1/shell/schedule-status"), {
    method: "GET",
    timeoutMs: options.timeoutMs || 5000,
  })
  return unwrapApiData(response, {
    enabled: false,
    should_run: true,
    next_action: "none",
    reason: "unavailable",
  })
}

async function applyScheduleTickViaApi(baseUrl, options = {}) {
  const request = options.requestJson || requestJson
  const response = await request(buildApiUrl(baseUrl, "/api/v1/shell/schedule/tick"), {
    method: "POST",
    timeoutMs: options.timeoutMs || 5000,
  })
  return unwrapApiData(response, { action: "noop" })
}

async function shutdownManagedBackend(session) {
  if (!session || !session.managed || !session.child || typeof session.child.kill !== "function") {
    return false
  }
  if (!session.child.killed) {
    session.child.kill()
  }
  return true
}

function sleep(timeoutMs) {
  return new Promise((resolve) => setTimeout(resolve, timeoutMs))
}

module.exports = {
  buildBackendBaseUrl,
  buildApiUrl,
  ensureBackendSession,
  applyScheduleTickViaApi,
  getSettingsViaApi,
  getScheduleStatusViaApi,
  getTrayStateViaApi,
  pauseRuntimeViaApi,
  probeBackend,
  requestJson,
  shutdownManagedBackend,
  spawnBackendProcess,
  startRuntimeViaApi,
  stopRuntimeViaApi,
  unwrapApiData,
}
