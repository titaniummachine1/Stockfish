# Game analysis benchmark (latest)

Binary: `src/stockfish.exe` · **8 threads** unless noted  
Modes: **full_id** = reference · **parity** = resume 2 strict 1 · **smart** = resume 2 strict 0 (speed, not depth-D parity)

| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs baseline |
|------|------|-------|-------|---------|---------|-------|-----|-------------|
| opening_6 | integrated_parity | 7 | 10 | 1 | 269 | 556155 | 2067490 | baseline |
| opening_6 | integrated_smart | 7 | 10 | 1 | 134 | 305467 | 2279604 | 0.50x |
| opening_6 | integrated_full_id | 7 | 10 | 1 | 169 | 389970 | 2307514 | 0.63x |
| opening_6 | uci_session | 7 | 10 | 1 | 628 | 458342 | 729843 | 2.33x |
| opening_6 | uci_fresh | 7 | 10 | 1 | 3294 | 658335 | 199858 | 12.25x |
| long_20 | integrated_parity | 21 | 8 | 1 | 190 | 439115 | 2311131 | baseline |
| long_20 | integrated_smart | 21 | 8 | 1 | 88 | 147967 | 1681443 | 0.46x |
| long_20 | integrated_full_id | 21 | 8 | 1 | 192 | 415247 | 2162744 | 1.01x |
| long_20 | uci_session | 21 | 8 | 1 | 579 | 389834 | 673288 | 3.05x |

Full table: `benchmark_20260605_021131.md`

**Quality (1 thread):** `STOCKFISH_THREADS=1 python scripts/gameanalysis_quality.py src/stockfish.exe` — **PASSED** (strict 1 vs full_id).

**Quick @ 1 thread:** `parity_h1` ≈100% nodes vs full, 100% score parity; `smart_h1` ≈79% nodes (speed mode).
