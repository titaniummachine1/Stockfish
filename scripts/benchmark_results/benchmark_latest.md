# Game analysis benchmark (latest)

Binary: `src/stockfish.exe` · **8 threads** · `feature/game-analysis-poc` post-`16eb840a`  
Run: `python scripts/benchmark_game_analysis.py src/stockfish.exe`

| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs integrated |
|------|------|-------|-------|---------|---------|-------|-----|---------------|
| club_1400 | integrated_pgn_full_id | 37 | 10 | 1 | 1019 | 1829554 | 1795440 | 1.00x |
| club_1400 | integrated_pgn_legacy | 37 | 10 | 1 | 579 | 778771 | 1345027 | 1.00x |
| club_1400 | integrated_pgn_smart | 37 | 10 | 1 | 748 | 1469805 | 1964979 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_full_id | 58 | 10 | 1 | 1683 | 3391669 | 2015251 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_legacy | 58 | 10 | 1 | 657 | 872827 | 1328503 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_smart | 58 | 10 | 1 | 1378 | 2913737 | 2114468 | 1.00x |
| rapid_600_style | integrated_pgn_full_id | 21 | 10 | 1 | 524 | 1243281 | 2372673 | 1.00x |
| rapid_600_style | integrated_pgn_legacy | 21 | 10 | 1 | 390 | 560959 | 1438356 | 1.00x |
| rapid_600_style | integrated_pgn_smart | 21 | 10 | 1 | 306 | 599129 | 1957937 | 1.00x |
| opening_6 | integrated_cold1 | 7 | 10 | 1 | 160 | 372076 | 2325475 | 1.78x |
| opening_6 | integrated_full_id | 7 | 10 | 1 | 177 | 415161 | 2345542 | 1.97x |
| opening_6 | integrated_legacy | 7 | 10 | 1 | 127 | 200222 | 1576551 | 1.41x |
| opening_6 | integrated_smart | 7 | 10 | 1 | 90 | 190390 | 2115444 | baseline |
| opening_6 | uci_fresh | 7 | 10 | 1 | 3003 | 386483 | 128698 | 33.37x |
| opening_6 | uci_session | 7 | 10 | 1 | 632 | 586624 | 928202 | 7.02x |
| tactical_14 | integrated_cold1 | 2 | 10 | 1 | 129 | 206915 | 1603992 | 1.25x |
| tactical_14 | integrated_full_id | 2 | 10 | 1 | 32 | 62378 | 1949312 | 0.31x |
| tactical_14 | integrated_legacy | 2 | 10 | 1 | 15 | 19271 | 1284733 | 0.15x |
| tactical_14 | integrated_smart | 2 | 10 | 1 | 103 | 193094 | 1874699 | baseline |
| tactical_14 | uci_fresh | 2 | 10 | 1 | 857 | 52302 | 61029 | 8.32x |
| tactical_14 | uci_session | 2 | 10 | 1 | 558 | 224957 | 403148 | 5.42x |
| endgame_8 | integrated_cold1 | 5 | 12 | 1 | 220 | 907663 | 4125740 | 0.94x |
| endgame_8 | integrated_full_id | 5 | 12 | 1 | 201 | 838257 | 4170432 | 0.86x |
| endgame_8 | integrated_legacy | 5 | 12 | 1 | 99 | 289462 | 2923858 | 0.42x |
| endgame_8 | integrated_smart | 5 | 12 | 1 | 233 | 906369 | 3889995 | baseline |
| endgame_8 | uci_fresh | 5 | 12 | 1 | 2224 | 1033610 | 464752 | 9.55x |
| endgame_8 | uci_session | 5 | 12 | 1 | 645 | 1088531 | 1687644 | 2.77x |
| opening_6_multipv3 | integrated_cold1 | 7 | 8 | 3 | 207 | 553075 | 2671859 | 1.05x |
| opening_6_multipv3 | integrated_full_id | 7 | 8 | 3 | 208 | 559585 | 2690312 | 1.05x |
| opening_6_multipv3 | integrated_legacy | 7 | 8 | 3 | 231 | 422666 | 1829722 | 1.17x |
| opening_6_multipv3 | integrated_smart | 7 | 8 | 3 | 198 | 378033 | 1909257 | baseline |
| opening_6_multipv3 | uci_fresh | 7 | 8 | 3 | 3213 | 760075 | 236562 | 16.23x |
| opening_6_multipv3 | uci_session | 7 | 8 | 3 | 608 | 512770 | 843371 | 3.07x |
| long_20 | integrated_cold1 | 21 | 8 | 1 | 208 | 492154 | 2366125 | 1.53x |
| long_20 | integrated_full_id | 21 | 8 | 1 | 146 | 327711 | 2244595 | 1.07x |
| long_20 | integrated_legacy | 21 | 8 | 1 | 175 | 240124 | 1372137 | 1.29x |
| long_20 | integrated_smart | 21 | 8 | 1 | 136 | 274046 | 2015044 | baseline |
| long_20 | uci_fresh | 21 | 8 | 1 | 8771 | 657559 | 74969 | 64.49x |
| long_20 | uci_session | 21 | 8 | 1 | 612 | 474453 | 775250 | 4.50x |

**Quick sweep:** `smart_h1` ~64% nodes vs full, **100%** MPV1 score parity on `opening_6` (see `scripts/benchmark_results/quick/latest.json`).
