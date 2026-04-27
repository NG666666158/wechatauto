param()

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$StateDir = Join-Path $ProjectRoot "wechat_ai\data\app\processes"
$AppDir = Join-Path $ProjectRoot "wechat_ai\data\app"
$PidFile = Join-Path $StateDir "runtime.pid"
$StopFile = Join-Path $AppDir "force_stop.flag"

New-Item -ItemType Directory -Force -Path $StateDir, $AppDir | Out-Null
Set-Content -Path $StopFile -Value "stop" -Encoding UTF8
Write-Host "[runtime] force_stop.flag written: $StopFile"

if (Test-Path $PidFile) {
    $raw = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    $pidValue = 0
    if ([int]::TryParse([string]$raw, [ref]$pidValue)) {
        Start-Sleep -Milliseconds 800
        $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $pidValue -Force
            Write-Host "[runtime] stopped pid=$pidValue"
        } else {
            Write-Host "[runtime] process already exited pid=$pidValue"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[runtime] pid file missing; stop flag still written for orphan worker"
}

Write-Host "runtime worker stopped. Backend/frontend services are untouched."
