# Game analysis benchmarks

Compares **integrated** `gameanalysis` vs how a typical external app talks to Stockfish.

## Modes

| Mode | Meaning |
|------|---------|
| `integrated` | `stockfish.exe gameanalysis depth D fen ... moves ...` (`cold 0`, hot TT) |
| `integrated_cold1` | Same, but `search_clear()` once at game start |
| `uci_session` | One UCI process: `position` + `go depth D` per ply (hot TT, like many backends) |
| `uci_fresh` | **New** `stockfish.exe` per ply (worst-case GUI; cold TT every time) |

**Same nodes** on `integrated` vs `uci_session` means the same chess work; wall-time gap is protocol/startup overhead.

## Run

```powershell
.\scripts\run-benchmark.ps1
# subset:
python scripts/benchmark_game_analysis.py src\stockfish.exe --cases opening_6,long_20
```

Results are written here as `benchmark_YYYYMMDD_HHMMSS.json` and `.md`.
