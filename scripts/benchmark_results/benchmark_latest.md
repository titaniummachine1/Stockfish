# Game analysis benchmark

Binary: `C:\gitProjects\Stockfish\src\stockfish.exe`

| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs integrated |
|------|------|-------|-------|---------|---------|-------|-----|---------------|
| club_1400 | integrated_pgn_full_id | 37 | 10 | 1 | 1021 | 2163902 | 2119394 | 1.00x |
| club_1400 | integrated_pgn_legacy | 37 | 10 | 1 | 575 | 1155943 | 2010335 | 1.00x |
| club_1400 | integrated_pgn_smart | 37 | 10 | 1 | 531 | 1279526 | 2409653 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_full_id | 58 | 10 | 1 | 1502 | 3489017 | 2322914 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_legacy | 58 | 10 | 1 | 1036 | 2210612 | 2133795 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_smart | 58 | 10 | 1 | 957 | 2273562 | 2375717 | 1.00x |
| rapid_600_style | integrated_pgn_full_id | 21 | 10 | 1 | 559 | 1382311 | 2472828 | 1.00x |
| rapid_600_style | integrated_pgn_legacy | 21 | 10 | 1 | 289 | 642447 | 2223000 | 1.00x |
| rapid_600_style | integrated_pgn_smart | 21 | 10 | 1 | 282 | 662481 | 2349223 | 1.00x |
| opening_6 | integrated_cold1 | 7 | 10 | 1 | 140 | 363972 | 2599800 | 1.30x |
| opening_6 | integrated_full_id | 7 | 10 | 1 | 170 | 400432 | 2355482 | 1.57x |
| opening_6 | integrated_legacy | 7 | 10 | 1 | 134 | 310970 | 2320671 | 1.24x |
| opening_6 | integrated_smart | 7 | 10 | 1 | 108 | 257414 | 2383462 | baseline |
| opening_6 | uci_fresh | 7 | 10 | 1 | 2946 | 631099 | 214222 | 27.28x |
| opening_6 | uci_session | 7 | 10 | 1 | 571 | 468018 | 819646 | 5.29x |
| tactical_14 | integrated_cold1 | 2 | 10 | 1 | 59 | 128569 | 2179135 | 0.68x |
| tactical_14 | integrated_full_id | 2 | 10 | 1 | 89 | 194262 | 2182719 | 1.02x |
| tactical_14 | integrated_legacy | 2 | 10 | 1 | 39 | 80693 | 2069051 | 0.45x |
| tactical_14 | integrated_smart | 2 | 10 | 1 | 87 | 192950 | 2217816 | baseline |
| tactical_14 | uci_fresh | 2 | 10 | 1 | 847 | 180004 | 212519 | 9.74x |
| tactical_14 | uci_session | 2 | 10 | 1 | 447 | 161381 | 361031 | 5.14x |
| endgame_8 | integrated_cold1 | 5 | 12 | 1 | 167 | 760776 | 4555544 | 0.99x |
| endgame_8 | integrated_full_id | 5 | 12 | 1 | 131 | 609148 | 4649984 | 0.78x |
| endgame_8 | integrated_legacy | 5 | 12 | 1 | 229 | 904752 | 3950882 | 1.36x |
| endgame_8 | integrated_smart | 5 | 12 | 1 | 168 | 751873 | 4475434 | baseline |
| endgame_8 | uci_fresh | 5 | 12 | 1 | 2244 | 838338 | 373590 | 13.36x |
| endgame_8 | uci_session | 5 | 12 | 1 | 600 | 918876 | 1531460 | 3.57x |
| opening_6_multipv3 | integrated_cold1 | 7 | 8 | 3 | 150 | 457415 | 3049433 | 1.27x |
| opening_6_multipv3 | integrated_full_id | 7 | 8 | 3 | 210 | 593537 | 2826366 | 1.78x |
| opening_6_multipv3 | integrated_legacy | 7 | 8 | 3 | 147 | 380401 | 2587761 | 1.25x |
| opening_6_multipv3 | integrated_smart | 7 | 8 | 3 | 118 | 299523 | 2538330 | baseline |
| opening_6_multipv3 | uci_fresh | 7 | 8 | 3 | 2914 | 694006 | 238162 | 24.69x |
| opening_6_multipv3 | uci_session | 7 | 8 | 3 | 559 | 509926 | 912211 | 4.74x |
| long_20 | integrated_cold1 | 21 | 8 | 1 | 152 | 383910 | 2525723 | 1.13x |
| long_20 | integrated_full_id | 21 | 8 | 1 | 175 | 451643 | 2580817 | 1.31x |
| long_20 | integrated_legacy | 21 | 8 | 1 | 140 | 296847 | 2120335 | 1.04x |
| long_20 | integrated_smart | 21 | 8 | 1 | 134 | 289793 | 2162634 | baseline |
| long_20 | uci_fresh | 21 | 8 | 1 | 8383 | 724643 | 86441 | 62.56x |
| long_20 | uci_session | 21 | 8 | 1 | 564 | 431880 | 765744 | 4.21x |
