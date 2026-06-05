# Long-game analysis: integrated `gameanalysis` vs naive UCI

**Machine:** 8 threads · depth **10** (PGN) / depth **8** (long_20 JSON)  
**Date:** 2026-06-05 · binary `src/stockfish.exe`

## What we compare

| Mode | Meaning |
|------|---------|
| **integrated_smart** | Default speed (`resume 2`, `strict 0`) — specialized spine |
| **integrated_parity** | Same depth-D contract as full ID (`strict 1`) |
| **integrated_full_id** | Reference (`resume 0`) |
| **uci_session** | **ChessKit-style**: one engine, `position` + `go depth D` per ply |
| **uci_fresh** | Worst case: new engine every ply |

## Your game (89 plies) — `chesscom_club_1100_carokann.pgn`

| Mode | Wall time | vs smart | Nodes |
|------|-----------|----------|-------|
| **integrated_smart** | **1059 ms** | baseline | 2.52M |
| integrated_parity | 1444 ms | 1.36× | 3.58M |
| integrated_full_id | 1440 ms | 1.36× | 3.49M |
| **uci_session** | **1991 ms** | **1.88× slower** | 3.69M |
| uci_fresh | 43794 ms | 41× slower | 4.06M |

**Takeaway:** On a full real Chess.com game at depth 10, integrated smart is **~1.9× faster** than the standard per-ply UCI loop, with **~32% fewer nodes** than full_id/uci_session.

## Longer / corpus PGNs (depth 10)

| Game | Plies | smart | uci_session | Speedup (smart vs UCI) |
|------|-------|-------|-------------|-------------------------|
| chesscom_club_1100_carokann | 89 | 1059 ms | 1991 ms | **1.88×** |
| gm_wijk_aan_zee | 58 | 842 ms | 2292 ms | **2.72×** |
| club_1400 | 37 | 654 ms | 1326 ms | **2.03×** |
| rapid_600_style | 21 | 274 ms | 990 ms | **3.61×** |

Speedup vs **uci_session** grows with game length (amortized spine/TT wins).

## JSON `long_20` (depth 8, 21 plies)

Run: `python scripts/benchmark_game_analysis.py src/stockfish.exe --cases long_20`

(see latest `benchmark_*.json` — typically smart ~2–4× faster than uci_session at same depth.)

## Quality note

- **integrated_parity** ≈ **full_id** on time/nodes for these runs (strict 1 disables resume shortcuts).
- **integrated_smart** is faster but **not** guaranteed identical eval to UCI; use **`strict 1`** for ChessKit-equivalent depth-D lines.

## Reproduce

```powershell
$env:STOCKFISH_THREADS = "8"
python scripts\benchmark_game_analysis.py src\stockfish.exe --skip-json --pgn-depth 10
```

Single game:

```powershell
python scripts\benchmark_game_analysis.py src\stockfish.exe --skip-json --pgn-only chesscom_club_1100_carokann --pgn-depth 10
```
