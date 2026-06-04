# One-time Windows dev setup for Stockfish build + instrumented tests.
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts\setup-windows-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Installing MSYS2 (if missing) ===" -ForegroundColor Cyan
if (-not (Test-Path "C:\msys64\usr\bin\bash.exe")) {
    winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements
}

Write-Host "=== Installing UCRT64 toolchain + diffutils ===" -ForegroundColor Cyan
C:\msys64\usr\bin\bash.exe -lc "pacman -Sy --noconfirm; pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-toolchain diffutils"

Write-Host "=== Python test dependency (requests) ===" -ForegroundColor Cyan
$Py = "${env:LOCALAPPDATA}\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
& $Py -m pip install --upgrade pip requests

Write-Host "=== Enable git post-commit hook ===" -ForegroundColor Cyan
Push-Location (Split-Path -Parent $PSScriptRoot)
git config core.hooksPath .githooks
Pop-Location

Write-Host "=== Done. Build + test: .\scripts\build-and-test.ps1 ===" -ForegroundColor Green
