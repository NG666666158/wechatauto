param(
    [string]$Duration = "30min",
    [double]$PollInterval = 1.0,
    [string]$ForceStopHotkey = "ctrl+shift+f12",
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$StateDir = Join-Path $ProjectRoot "wechat_ai\data\app\processes"
$AppDir = Join-Path $ProjectRoot "wechat_ai\data\app"
$LogDir = Join-Path $AppDir "logs"
New-Item -ItemType Directory -Force -Path $StateDir, $LogDir | Out-Null

$PidFile = Join-Path $StateDir "runtime.pid"
$StopFile = Join-Path $AppDir "force_stop.flag"
$LogFile = Join-Path $LogDir "runtime_worker.log"

if (Test-Path $PidFile) {
    $existing = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    $existingPid = 0
    if ([int]::TryParse([string]$existing, [ref]$existingPid) -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-Host "[runtime] already running pid=$existingPid"
        exit 0
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

if (Test-Path $StopFile) {
    Set-Content -Path $StopFile -Value "" -Encoding UTF8
}

$debugFlag = ""
if ($Debug) { $debugFlag = "--debug" }
$command = "py -3 scripts\run_minimax_global_auto_reply.py --duration $Duration --poll-interval $PollInterval --force-stop-hotkey $ForceStopHotkey --force-stop-file `"$StopFile`" $debugFlag"
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes(
    "Set-Location -LiteralPath '$ProjectRoot'; `$ErrorActionPreference='Continue'; $command *>> '$LogFile'"
))
$process = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded" -WindowStyle Normal -PassThru
Set-Content -Path $PidFile -Value $process.Id -Encoding UTF8
Write-Host "[runtime] started pid=$($process.Id) log=$LogFile stop_file=$StopFile hotkey=$ForceStopHotkey"
