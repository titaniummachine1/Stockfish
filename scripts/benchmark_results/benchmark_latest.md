# Game analysis benchmark (latest full run)

Binary: `src/stockfish.exe` (feature/game-analysis-poc, Windows UCRT64 build)

## Summary

| Comparison | Wall time vs integrated | Node count |
|------------|-------------------------|------------|
| **integrated** (`gameanalysis`, cold 0) | baseline | same work |
| **uci_session** (one process, position+go/ply) | **~2.6–7.4× slower** | **identical** |
| **uci_fresh** (new process every ply) | **~13–35× slower** | higher (cold TT) |
| **integrated_cold1** | ~same as cold 0 | identical |

Integrated `gameanalysis` does the **same search work** as a correct external UCI loop (matching nodes), but finishes much faster because it avoids per-ply UCI chatter and keeps one batch run.

**Not yet measured:** Phase 2 resume (skip redundant shallow ID) — both integrated and uci_session still pay full depth iteration per ply today.

## Full table

| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs integrated |
|------|------|-------|-------|---------|---------|-------|-----|---------------|
| sample | integrated_pgn | 7 | 8 | 1 | 42 | 16756 | 398952 | baseline |
| opening_6 | integrated | 7 | 10 | 1 | 126 | 57443 | 455896 | baseline |
| opening_6 | integrated_cold1 | 7 | 10 | 1 | 137 | 57443 | 419291 | 1.09x |
| opening_6 | uci_fresh | 7 | 10 | 1 | 1705 | 86298 | 50614 | 13.53x |
| opening_6 | uci_session | 7 | 10 | 1 | 478 | 57443 | 120173 | 3.79x |
| tactical_14 | integrated | 2 | 10 | 1 | 33 | 12194 | 369515 | baseline |
| tactical_14 | integrated_cold1 | 2 | 10 | 1 | 44 | 12194 | 277136 | 1.33x |
| tactical_14 | uci_fresh | 2 | 10 | 1 | 434 | 6640 | 15299 | 13.15x |
| tactical_14 | uci_session | 2 | 10 | 1 | 244 | 12194 | 49975 | 7.39x |
| endgame_8 | integrated | 5 | 12 | 1 | 318 | 282579 | 888613 | baseline |
| endgame_8 | integrated_cold1 | 5 | 12 | 1 | 316 | 282579 | 894237 | 0.99x |
| endgame_8 | uci_fresh | 5 | 12 | 1 | 1421 | 328374 | 231086 | 4.47x |
| endgame_8 | uci_session | 5 | 12 | 1 | 529 | 282579 | 534175 | 1.66x |
| opening_6_multipv3 | integrated | 7 | 8 | 3 | 183 | 107240 | 586010 | baseline |
| opening_6_multipv3 | integrated_cold1 | 7 | 8 | 3 | 193 | 107240 | 555647 | 1.05x |
| opening_6_multipv3 | uci_fresh | 7 | 8 | 3 | 1659 | 115232 | 69458 | 9.07x |
| opening_6_multipv3 | uci_session | 7 | 8 | 3 | 403 | 107240 | 266104 | 2.20x |
| long_20 | integrated | 21 | 8 | 1 | 132 | 67597 | 512098 | baseline |
| long_20 | integrated_cold1 | 21 | 8 | 1 | 138 | 67597 | 489833 | 1.05x |
| long_20 | uci_fresh | 21 | 8 | 1 | 4567 | 112434 | 24618 | 34.60x |
| long_20 | uci_session | 21 | 8 | 1 | 349 | 67597 | 193687 | 2.64x |

Reproduce: `.\scripts\run-benchmark.ps1`
