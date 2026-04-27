param()

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$StateDir = Join-Path $ProjectRoot "wechat_ai\data\app\processes"

function Get-PidStatus([string]$Name, [string]$PidFile) {
    if (-not (Test-Path $PidFile)) {
        return [pscustomobject]@{ name = $Name; pid = $null; running = $false; source = $PidFile }
    }
    $raw = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $pidValue = 0
    $running = $false
    if ([int]::TryParse([string]$raw, [ref]$pidValue)) {
        $running = [bool](Get-Process -Id $pidValue -ErrorAction SilentlyContinue)
    }
    return [pscustomobject]@{ name = $Name; pid = $pidValue; running = $running; source = $PidFile }
}

@(
    Get-PidStatus "backend" (Join-Path $StateDir "backend.pid")
    Get-PidStatus "frontend" (Join-Path $StateDir "frontend.pid")
    Get-PidStatus "runtime" (Join-Path $StateDir "runtime.pid")
) | Format-Table -AutoSize
