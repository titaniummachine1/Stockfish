# Run after git commit: build Stockfish and run instrumented tests.
$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src   = Join-Path $Root "src"
$Tests = Join-Path $Root "tests"

function Find-Make {
    $names = @("make", "mingw32-make", "gmake")
    foreach ($n in $names) {
        $c = Get-Command $n -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    $candidates = @(
        "C:\msys64\ucrt64\bin\mingw32-make.exe",
        "C:\msys64\mingw64\bin\mingw32-make.exe",
        "C:\msys64\usr\bin\make.exe",
        "C:\Program Files\Git\usr\bin\make.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$Make = Find-Make
if (-not $Make) {
    Write-Host "SKIP post-commit build: 'make' not found. Install MSYS2/Git-Bash make or run from src: make -j build" -ForegroundColor Yellow
    exit 0
}

Write-Host "=== post-commit: build ($Make) ===" -ForegroundColor Cyan
Push-Location $Src
try {
    & $Make -j build 2>&1 | Tee-Object -FilePath (Join-Path $Root "build-last.log")
    if ($LASTEXITCODE -ne 0) { throw "build failed with exit $LASTEXITCODE" }
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
    if ($LASTEXITCODE -ne 0) { throw "instrumented.py failed with exit $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "=== post-commit: OK ===" -ForegroundColor Green
