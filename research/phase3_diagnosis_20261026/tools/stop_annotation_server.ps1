$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPidFile=Join-Path $taskRoot 'results\annotation_range_server_pid.txt'
$taskProcessId=[int](Get-Content -LiteralPath $taskPidFile -Raw).Trim()
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId = $taskProcessId"
if (-not $taskProcess) { Write-Output 'Annotation server already stopped'; exit 0 }
if ($taskProcess.CommandLine -notmatch 'tools[/\\]annotation_server\.py --port 8779') { throw 'PID no longer belongs to this annotation server' }
$taskListener=Get-NetTCPConnection -LocalPort 8779 -State Listen -ErrorAction SilentlyContinue
if ($taskListener -and $taskListener.OwningProcess -ne $taskProcessId) { throw 'Port now belongs to a different process' }
Stop-Process -Id $taskProcessId
Write-Output 'Stopped the task-local annotation server'
