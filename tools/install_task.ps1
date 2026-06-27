# install_task.ps1
# Registers a Windows Task Scheduler job that runs the screener pipeline
# daily at 4:05 PM (after NSE market close at 3:30 PM + buffer).
#
# Run ONCE as Administrator:
#   Right-click PowerShell -> "Run as Administrator"
#   cd "C:\Users\dhara\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools"
#   .\install_task.ps1

$taskName   = "Trading_Screener_Pipeline"
$scriptPath = Join-Path $PSScriptRoot "screener_pipeline.py"
$logPath    = Join-Path $PSScriptRoot "pipeline.log"

# Locate the py launcher
$pyExe = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $pyExe) {
    Write-Error "Python launcher 'py' not found. Install Python from python.org."
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute    $pyExe `
    -Argument   "-3 `"$scriptPath`"" `
    -WorkingDirectory (Split-Path $scriptPath)

# Daily at 4:05 PM; also runs if the machine was off at trigger time
$trigger = New-ScheduledTaskTrigger -Daily -At "16:05"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName  $taskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force | Out-Null

Write-Host ""
Write-Host "Task '$taskName' registered." -ForegroundColor Green
Write-Host "  Runs daily at 4:05 PM (NSE close + 35 min buffer)"
Write-Host "  Script : $scriptPath"
Write-Host "  Log    : $logPath"
Write-Host ""
Write-Host "--- Quick commands ---"
Write-Host "  Run now      :  py -3 `"$scriptPath`""
Write-Host "  Check status :  Get-ScheduledTask -TaskName '$taskName' | Select-Object State"
Write-Host "  Remove task  :  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
