# Build Stockfish (MSYS2 UCRT64) and run instrumented.py
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$env:PATH = "C:\msys64\usr\bin;C:\msys64\ucrt64\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

& "$PSScriptRoot\post-commit-build-test.ps1"
