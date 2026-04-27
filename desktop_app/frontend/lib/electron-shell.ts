export type DesktopShellPreferences = {
  launchAtLogin: boolean
  scheduleTickIntervalSeconds: number
}

type DesktopShellPatch = Partial<DesktopShellPreferences>

type ElectronShellApi = {
  getPreferences: () => Promise<DesktopShellPreferences>
  updatePreferences: (patch: DesktopShellPatch) => Promise<DesktopShellPreferences>
}

declare global {
  interface Window {
    wechatDesktopShell?: ElectronShellApi
  }
}

export function getDesktopShellBridge() {
  const bridge = typeof window === "undefined" ? undefined : window.wechatDesktopShell

  return {
    isAvailable() {
      return Boolean(bridge)
    },
    async getPreferences(): Promise<DesktopShellPreferences | null> {
      if (!bridge) {
        return null
      }
      return bridge.getPreferences()
    },
    async updatePreferences(patch: DesktopShellPatch): Promise<DesktopShellPreferences | null> {
      if (!bridge) {
        return null
      }
      return bridge.updatePreferences(patch)
    },
  }
}
