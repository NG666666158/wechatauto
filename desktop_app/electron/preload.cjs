const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("wechatDesktopShell", {
  getPreferences: () => ipcRenderer.invoke("shell-preferences:get"),
  updatePreferences: (patch) => ipcRenderer.invoke("shell-preferences:update", patch || {}),
})
