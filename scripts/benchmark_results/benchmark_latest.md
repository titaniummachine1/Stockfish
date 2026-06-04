# Game analysis benchmark

Binary: `C:\gitProjects\Stockfish\src\stockfish.exe`

| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs integrated |
|------|------|-------|-------|---------|---------|-------|-----|---------------|
| club_1400 | integrated_pgn_full_id | 37 | 10 | 1 | 975 | 2052254 | 2104875 | 1.00x |
| club_1400 | integrated_pgn_legacy | 37 | 10 | 1 | 908 | 1202461 | 1324296 | 1.00x |
| club_1400 | integrated_pgn_smart | 37 | 10 | 1 | 928 | 1802700 | 1942564 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_full_id | 58 | 10 | 1 | 1721 | 3405889 | 1979017 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_legacy | 58 | 10 | 1 | 977 | 1310882 | 1341742 | 1.00x |
| gm_wijk_aan_zee | integrated_pgn_smart | 58 | 10 | 1 | 1677 | 2659869 | 1586087 | 1.00x |
| rapid_600_style | integrated_pgn_full_id | 21 | 10 | 1 | 500 | 1225490 | 2450980 | 1.00x |
| rapid_600_style | integrated_pgn_legacy | 21 | 10 | 1 | 435 | 684024 | 1572468 | 1.00x |
| rapid_600_style | integrated_pgn_smart | 21 | 10 | 1 | 361 | 772573 | 2140091 | 1.00x |
| opening_6 | integrated_cold1 | 7 | 10 | 1 | 164 | 395301 | 2410371 | 1.00x |
| opening_6 | integrated_full_id | 7 | 10 | 1 | 162 | 415961 | 2567660 | 0.99x |
| opening_6 | integrated_legacy | 7 | 10 | 1 | 119 | 216666 | 1820722 | 0.73x |
| opening_6 | integrated_smart | 7 | 10 | 1 | 164 | 339675 | 2071189 | baseline |
| opening_6 | uci_fresh | 7 | 10 | 1 | 2939 | 494068 | 168107 | 17.92x |
| opening_6 | uci_session | 7 | 10 | 1 | 557 | 404582 | 726359 | 3.40x |
| tactical_14 | integrated_cold1 | 2 | 10 | 1 | 126 | 262595 | 2084087 | 1.68x |
| tactical_14 | integrated_full_id | 2 | 10 | 1 | 89 | 188566 | 2118719 | 1.19x |
| tactical_14 | integrated_legacy | 2 | 10 | 1 | 27 | 40986 | 1518000 | 0.36x |
| tactical_14 | integrated_smart | 2 | 10 | 1 | 75 | 160467 | 2139560 | baseline |
| tactical_14 | uci_fresh | 2 | 10 | 1 | 853 | 182491 | 213940 | 11.37x |
| tactical_14 | uci_session | 2 | 10 | 1 | 456 | 123900 | 271710 | 6.08x |
| endgame_8 | integrated_cold1 | 5 | 12 | 1 | 306 | 1424004 | 4653607 | 1.46x |
| endgame_8 | integrated_full_id | 5 | 12 | 1 | 162 | 746606 | 4608679 | 0.77x |
| endgame_8 | integrated_legacy | 5 | 12 | 1 | 157 | 434293 | 2766197 | 0.75x |
| endgame_8 | integrated_smart | 5 | 12 | 1 | 210 | 933409 | 4444804 | baseline |
| endgame_8 | uci_fresh | 5 | 12 | 1 | 2057 | 741883 | 360662 | 9.80x |
| endgame_8 | uci_session | 5 | 12 | 1 | 650 | 1258640 | 1936369 | 3.10x |
| opening_6_multipv3 | integrated_cold1 | 7 | 8 | 3 | 216 | 589471 | 2729032 | 0.78x |
| opening_6_multipv3 | integrated_full_id | 7 | 8 | 3 | 221 | 604472 | 2735167 | 0.80x |
| opening_6_multipv3 | integrated_legacy | 7 | 8 | 3 | 238 | 418848 | 1759865 | 0.86x |
| opening_6_multipv3 | integrated_smart | 7 | 8 | 3 | 277 | 576427 | 2080963 | baseline |
| opening_6_multipv3 | uci_fresh | 7 | 8 | 3 | 2950 | 736853 | 249780 | 10.65x |
| opening_6_multipv3 | uci_session | 7 | 8 | 3 | 584 | 517902 | 886818 | 2.11x |
| long_20 | integrated_cold1 | 21 | 8 | 1 | 180 | 460557 | 2558650 | 0.86x |
| long_20 | integrated_full_id | 21 | 8 | 1 | 142 | 353899 | 2492246 | 0.68x |
| long_20 | integrated_legacy | 21 | 8 | 1 | 205 | 296634 | 1446995 | 0.98x |
| long_20 | integrated_smart | 21 | 8 | 1 | 209 | 377364 | 1805569 | baseline |
| long_20 | uci_fresh | 21 | 8 | 1 | 8482 | 754247 | 88923 | 40.58x |
| long_20 | uci_session | 21 | 8 | 1 | 546 | 421890 | 772692 | 2.61x |
