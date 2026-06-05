# Optional: Maia vs Maia UCI self-play -> benchmark PGN (requires Maia engine on PATH).
$ErrorActionPreference = "Stop"
$Maia = $env:MAIA_PATH
if (-not $Maia) {
    foreach ($p in @("maia", "maia.exe", "C:\maia\maia.exe")) {
        if (Get-Command $p -ErrorAction SilentlyContinue) { $Maia = (Get-Command $p).Source; break }
    }
}
if (-not $Maia) {
    Write-Host "Maia not found. Set MAIA_PATH or install Maia UCI, then re-run." -ForegroundColor Yellow
    Write-Host "See https://github.com/CSSLab/maia-chess"
    exit 0
}
Write-Host "Maia found: $Maia — self-play export not yet automated; use Lichess PGN for now." -ForegroundColor Yellow
