# Game-analysis benchmark (latest)

Binary: `src/stockfish.exe` · **8 threads** · depth **10** PGN corpus  
**Build:** 2026-06-05 — TT-cap resume, virtual aspiration ladder, default `resume 3` (merge)

## vs `uci_session` (ChessKit-style per-ply UCI)

| Game | Plies | merge | smart (r2) | uci_session | merge speedup |
|------|-------|-------|------------|-------------|---------------|
| chesscom_club_1100_carokann | 89 | 2685 ms | 2418 ms | 3466 ms | **1.29×** |
| gm_wijk_aan_zee | 58 | 1900 ms | 2736 ms | 3454 ms | **1.82×** |
| rapid_600_style | 21 | 560 ms | 1016 ms | 1386 ms | **2.47×** |
| club_1400 | 37 | 1985 ms | 2101 ms | 2489 ms | **1.25×** |

Nodes (merge vs uci_session): chesscom **−19%**, gm_wijk **−34%**, rapid **−30%**.

## Modes

| Mode | When |
|------|------|
| `integrated_merge` | `resume 3` (default), `refine 1`, `strict 0` |
| `integrated_smart` | `resume 2`, same |
| `integrated_parity` | `strict 1` — depth-D score parity CI |
| `uci_session` | One process, `position` + `go depth` per ply |

## Quality

`STOCKFISH_THREADS=1 python scripts/gameanalysis_quality.py src/stockfish.exe` — **PASSED** (strict 1 vs full_id).

Smart/merge eval paths are **not** score-gated in CI; use `strict 1` for ChessKit parity.

## Reproduce

```powershell
$env:STOCKFISH_THREADS="8"
python scripts\benchmark_game_analysis.py src\stockfish.exe --skip-json --pgn-depth 10
```
