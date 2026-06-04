# Quick manual experiments: PGN + a few positions (prints gameanalysis output).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe  = Join-Path $Root "src\stockfish.exe"
$Pgn  = Join-Path $Root "tests\sample.pgn"

function Run-Ga($Label, [string[]]$GaArgs) {
    Write-Host "`n=== $Label ===" -ForegroundColor Cyan
    $all = @($Exe) + $GaArgs
    $p = Start-Process -FilePath $Exe -ArgumentList $GaArgs -NoNewWindow -PassThru -RedirectStandardOutput "$env:TEMP\ga_out.txt" -Wait
    if ($p.ExitCode -ne 0) { Write-Host "Exit $($p.ExitCode)" -ForegroundColor Red }
    Get-Content "$env:TEMP\ga_out.txt" | Where-Object { $_ -match "gameanalysis" }
}

Run-Ga "PGN sample depth 10" @("gameanalysis", "depth", "10", "pgn", $Pgn)
Run-Ga "Tactical FEN depth 12 multipv 2" @(
    "gameanalysis", "depth", "12", "multipv", "2",
    "fen", "rq3rk1/ppp2ppp/1bnpb3/3N2B1/3NP3/7P/PPPQ1PP1/2KR3R", "w", "-", "-", "7", "14",
    "moves", "d4e6"
)
Run-Ga "Endgame depth 14" @(
    "gameanalysis", "depth", "14",
    "fen", "2K5/p7/7P/5pR1/8/5k2/r7/8", "w", "-", "-", "0", "1",
    "moves", "g5g6", "f3e3"
)
