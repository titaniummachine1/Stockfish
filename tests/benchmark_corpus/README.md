# Benchmark PGN corpus

Balanced whole-game samples for `gameanalysis` benchmarks.

| File | Source | Notes |
|------|--------|-------|
| `gm_wijk_aan_zee.pgn` | Carlsen–Wang Hao, Tata Steel 2011 | 57 moves, validated SAN |
| `club_1400.pgn` | Club rapid (lichess-style) | 36 moves, validated SAN |
| `rapid_600_style.pgn` | Ruy Lopez spine (`benchmark_games` long_20) | 20 moves |

Regenerate after edits:

```powershell
python scripts/generate_benchmark_corpus.py
```

## Refresh from the internet

```powershell
.\scripts\download_benchmark_corpus.ps1
```

Uses Lichess **public** game exports (no account). You can also paste any PGN:

```text
gameanalysis depth 12 pgn C:\path\to\game.pgn
```

## Maia self-play (optional)

If [Maia](https://github.com/CSSLab/maia-chess) is installed:

```powershell
.\scripts\generate_maia_benchmark_games.ps1
```

Writes `tests/benchmark_corpus/maia_selfplay.pgn` for repeatable low-overhead benchmarks.
