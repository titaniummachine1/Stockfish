# Game-analysis experiments (minimal)

## User idea: spine tree merge
One game analysis reuses search tree across plies. **Implemented as:**
- `spineContinueTt` — skip `tt.new_search()` after ply 0 (same TT generation = parent subtrees stay hot).
- `resume 3` — merge mode: tighter horizon, PV-tail move order, slightly lower `spineTtMinDepth` on best PV moves.
- Existing `startDepth` + `spineTtMinDepth` = ID + TT depth floor (horizon guard).

Full single-tree search inside one `go` is **not** done (would need custom Search loop); TT+warm ID is the practical merge.

## Branches
- `feature/game-analysis-poc` — stable integration
- `exp/spine-tt-merge` — TT merge + resume 3

## Results (2026-06-04 quick ~12min, 8 threads)
| config | ~nodes vs full | quality | wall |
|--------|----------------|---------|------|
| smart_h1 (r2,h1) | 82% | 100% | fastest |
| merge_h1 (r3,h1) | 86% | 100% | fastest |
| smart_h2 (r2,h2) | 94% | 100% | slower |
| merge_h2 | 85% | 100% | mid |

**Ship:** `spineContinueTt` + default `resumeHorizon=1`. Optional `resume 3` for merge mode.
**Not shipped:** single `go` spanning whole game (needs Search refactor).
