# Start multi-hour game-analysis experiments (background).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe  = Join-Path $Root "src\stockfish.exe"
$Py   = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

if (-not $env:STOCKFISH_THREADS) {
    $logical = (Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue).NumberOfLogicalProcessors
    if ($logical) { $env:STOCKFISH_THREADS = "$logical" }
}

$LogDir = Join-Path $Root "scripts\benchmark_results\experiments"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "runner_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

$Hours = if ($args.Count -gt 0) { [double]$args[0] } else { 10.0 }

Write-Host "Starting experiments for $Hours hours -> $LogFile"
Start-Process -FilePath $Py -ArgumentList @(
    "$Root\scripts\run_long_experiments.py",
    $Exe,
    "--hours", "$Hours"
) -RedirectStandardOutput $LogFile -RedirectStandardError "${LogFile}.err" -NoNewWindow

Write-Host "PID logging to $LogFile"
Write-Host "Tail: Get-Content $LogFile -Wait"
