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

## Results (2026-06-05 quick ~8min, 8 threads)
| config | ~nodes vs full | quality | wall |
|--------|----------------|---------|------|
| smart_h1 (r2,h1) | 64% | 100% | ~156 ms mean |
| merge_h1 (r3,h1) | 62% | 100% | ~152 ms mean |

Note: `resume 3` is currently the same spine policy as `2` in `compute_spine_step`.

**Ship:** `spineContinueTt`, spine resume (PV vs off-PV), `refine 1` deepen pass.  
**2026-06-05:** skip refine when all plies already at depth; incremental prefix on refine walk.  
**Not shipped:** single `go` spanning whole game (needs Search refactor).

Full audit: `exp/AUDIT.md`
