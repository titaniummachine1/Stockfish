# Download extra benchmark PGNs from Lichess public exports (optional).
$ErrorActionPreference = "Stop"
$Out = Join-Path (Split-Path -Parent $PSScriptRoot) "tests\benchmark_corpus"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

# Example: replace GAME_ID with a lichess game URL id (12 chars).
# Invoke-WebRequest -Uri "https://lichess.org/game/export/GAME_ID" -OutFile "$Out\lichess_custom.pgn"

Write-Host "Corpus folder: $Out" -ForegroundColor Cyan
Write-Host "Bundled: gm_wijk_aan_zee.pgn, club_1400.pgn, rapid_600_style.pgn"
Write-Host "To add a game: download from https://lichess.org -> Share -> Export PGN"
Write-Host "Then: gameanalysis depth 12 pgn path\to\file.pgn"
