# Game-analysis benchmark (latest)

Binary: `src/stockfish.exe` · depth **10** · chesscom 89 plies

## Whole-game oneshot (`oneshot 1`, default)

| Threads | Mode | Time | Nodes | vs uci_session |
|---------|------|------|-------|----------------|
| **1** | oneshot/resume | **~47s** | ~443k | N/A (oneshot path) |
| **8** | resume (per-ply) | **~1.3s** | ~2.6M | **~1.9×** |

- **1 thread:** single `go` walks all 89 plies inside `Search` (no per-ply thread pool restart).
- **8+ threads:** oneshot disabled until worker barriers are fixed; uses fast per-ply path (TT merge + resume).

## Quality

`STOCKFISH_THREADS=1 python scripts/gameanalysis_quality.py` — **PASSED** (strict 1 vs full_id).

## Flags

| Flag | Meaning |
|------|---------|
| `oneshot 1` | Whole game in one search (1 thread only) |
| `oneshot 0` | Legacy per-ply `go` |
| `resume 3` | TT-merge (default) |
| `strict 1` | Depth-D parity |
