# Run game-analysis benchmark (integrated vs external UCI).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe  = Join-Path $Root "src\stockfish.exe"
$Py   = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

if (-not (Test-Path $Exe)) {
    Write-Host "Build first: scripts\msys-build.sh or scripts\build-and-test.ps1" -ForegroundColor Yellow
    exit 1
}

$args = @("$Root\scripts\benchmark_game_analysis.py", $Exe) + $args
& $Py @args
