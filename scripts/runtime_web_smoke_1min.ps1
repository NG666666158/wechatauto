param(
    [string]$BaseUrl = "http://127.0.0.1:8765/api/v1",
    [int]$DurationSeconds = 65,
    [int]$ReadyTimeoutSeconds = 120,
    [int]$NarratorSettleSeconds = 10
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $ProjectRoot

function Invoke-JsonPost([string]$Path, [hashtable]$Body) {
    $json = $Body | ConvertTo-Json -Depth 8
    Invoke-RestMethod -Uri "$BaseUrl$Path" -Method Post -ContentType "application/json" -Body $json
}

$runtimePayload = @{
    mode = "global"
    ready_timeout_seconds = $ReadyTimeoutSeconds
    poll_interval_seconds = 1
    narrator_settle_seconds = $NarratorSettleSeconds
    wait_for_ui_ready_before_guardian = $true
}

Write-Host "[smoke] force stop any stale runtime"
try {
    Invoke-RestMethod -Uri "$BaseUrl/runtime/force-stop" -Method Post | Out-Null
} catch {
    Write-Host "[smoke] force stop ignored: $($_.Exception.Message)"
}

Write-Host "[smoke] bootstrap-check"
$check = Invoke-JsonPost "/runtime/bootstrap-check" $runtimePayload
$check.data.bootstrap | ConvertTo-Json -Depth 8

Write-Host "[smoke] bootstrap-start"
$start = Invoke-JsonPost "/runtime/bootstrap-start" $runtimePayload
$start.data | ConvertTo-Json -Depth 8

Write-Host "[smoke] runtime is running for $DurationSeconds seconds. Send friend and group @ messages now."
Start-Sleep -Seconds $DurationSeconds

Write-Host "[smoke] stop runtime"
$stop = Invoke-RestMethod -Uri "$BaseUrl/runtime/stop" -Method Post
$stop.data | ConvertTo-Json -Depth 8

Write-Host "[smoke] recent runtime events"
$env:PYTHONIOENCODING = "utf-8"
py -3 -c "import json,pathlib; p=pathlib.Path('wechat_ai/data/logs/runtime_events.jsonl'); events=[]; cutoff=''; lines=p.read_text(encoding='utf-8').splitlines()[-80:] if p.exists() else []; [print(json.dumps(json.loads(line), ensure_ascii=False)) for line in lines if line.strip()]"

Write-Host "[smoke] recent conversations"
py -3 -c "import json,pathlib; p=pathlib.Path('wechat_ai/data/app/conversations.json'); data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; [print('## '+cid+' '+str(rec.get('title'))+' group='+str(rec.get('is_group'))+'\n'+'\n'.join(json.dumps(m, ensure_ascii=False) for m in rec.get('messages', [])[-6:])) for cid, rec in data.items() if rec.get('messages')]"
