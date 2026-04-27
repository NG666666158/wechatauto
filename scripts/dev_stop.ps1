param()

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$StateDir = Join-Path $ProjectRoot "wechat_ai\data\app\processes"

function Stop-PidFileProcess([string]$Name, [string]$PidFile) {
    if (-not (Test-Path $PidFile)) {
        Write-Host "[$Name] not running (pid file missing)"
        return
    }
    $raw = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $pidValue = 0
    if ([int]::TryParse([string]$raw, [ref]$pidValue)) {
        $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($process) {
            taskkill /PID $pidValue /T /F | Out-Null
            Write-Host "[$Name] stopped pid=$pidValue"
        } else {
            Write-Host "[$Name] pid file stale pid=$pidValue"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

Stop-PidFileProcess "backend" (Join-Path $StateDir "backend.pid")
Stop-PidFileProcess "frontend" (Join-Path $StateDir "frontend.pid")
Write-Host "dev services stopped. Runtime worker is untouched."
