# Repeat 12-min experiment cycles until hours elapsed. Logs to benchmark_results/quick/
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Exe  = Join-Path $Root "src\stockfish.exe"
$Py   = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
if (-not $env:STOCKFISH_THREADS) { $env:STOCKFISH_THREADS = "8" }

$Hours = if ($args.Count -gt 0) { [double]$args[0] } else { 10.0 }
$End = (Get-Date).AddHours($Hours)
$Log = Join-Path $Root "scripts\benchmark_results\quick\autonomous.log"
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

"Started $(Get-Date) for $Hours h" | Tee-Object -FilePath $Log -Append
while ((Get-Date) -lt $End) {
    $t0 = Get-Date
    "=== cycle $(Get-Date -Format 'HH:mm:ss') ===" | Tee-Object -FilePath $Log -Append
    & $Py -u "$Root\scripts\run_quick_experiments.py" $Exe --minutes 12 2>&1 | Tee-Object -FilePath $Log -Append
    bash -lc "cd /c/gitProjects/Stockfish && bash scripts/msys-build.sh" 2>&1 | Select-Object -Last 3 | Tee-Object -FilePath $Log -Append
    "cycle done in $(((Get-Date) - $t0).TotalMinutes.ToString('0.0')) min" | Tee-Object -FilePath $Log -Append
}
"Finished $(Get-Date)" | Tee-Object -FilePath $Log -Append
