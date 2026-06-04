# Run after git commit: build Stockfish and run instrumented tests.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src  = Join-Path $Root "src"
$Tests = Join-Path $Root "tests"

Write-Host "=== post-commit: build ===" -ForegroundColor Cyan
Push-Location $Src
try {
    # Use native arch on Windows (make help for options)
    $env:Path = "$Src;" + $env:Path
    make -j build 2>&1 | Tee-Object -FilePath (Join-Path $Root "build-last.log")
    if ($LASTEXITCODE -ne 0) { throw "make build failed" }
}
finally {
    Pop-Location
}

$Exe = Join-Path $Src "stockfish.exe"
if (-not (Test-Path $Exe)) { $Exe = Join-Path $Src "stockfish" }
if (-not (Test-Path $Exe)) { throw "stockfish binary not found in src/" }

Write-Host "=== post-commit: instrumented.py ===" -ForegroundColor Cyan
Push-Location $Tests
try {
    python instrumented.py --none $Exe
    if ($LASTEXITCODE -ne 0) { throw "instrumented.py failed" }
}
finally {
    Pop-Location
}

Write-Host "=== post-commit: OK ===" -ForegroundColor Green
