# Run after git commit: build Stockfish and run instrumented tests.
$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src   = Join-Path $Root "src"
$Tests = Join-Path $Root "tests"

# MSYS diff for test_network_equals_base; avoid MSYS python shadowing Windows python
$env:PATH = "C:\msys64\usr\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

function Get-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return "python"
}

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
    # Prefer MSYS2 bash build (Stockfish Makefile needs sh/uname)
    $MsysBuild = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "msys-build.sh"
    if ((Test-Path "C:\msys64\usr\bin\bash.exe") -and (Test-Path $MsysBuild)) {
        return "@msys-bash:$MsysBuild"
    }
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
$Log = Join-Path $Root "build-last.log"
if ($Make -like "@msys-bash:*") {
    $Script = $Make.Substring(11)
    $env:MSYSTEM = "UCRT64"
    & C:\msys64\usr\bin\env.exe MSYSTEM=UCRT64 C:\msys64\usr\bin\bash.exe --login -c "bash '$($Script -replace '\\','/')" 2>&1 | Tee-Object -FilePath $Log
    if ($LASTEXITCODE -ne 0) { throw "build failed with exit $LASTEXITCODE" }
}
else {
    Push-Location $Src
    try {
        & $Make -j build 2>&1 | Tee-Object -FilePath $Log
        if ($LASTEXITCODE -ne 0) { throw "build failed with exit $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}

$Exe = Join-Path $Src "stockfish.exe"
if (-not (Test-Path $Exe)) { $Exe = Join-Path $Src "stockfish" }
if (-not (Test-Path $Exe)) { throw "stockfish binary not found in src/" }

Write-Host "=== post-commit: instrumented.py ===" -ForegroundColor Cyan
Push-Location $Tests
try {
    & (Get-Python) instrumented.py --none $Exe
    if ($LASTEXITCODE -ne 0) { throw "instrumented.py failed with exit $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "=== post-commit: OK ===" -ForegroundColor Green
