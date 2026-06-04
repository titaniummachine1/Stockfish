# Game-analysis audit (for return visit)

**Branch:** `feature/game-analysis-poc`  
**Base commit:** `16eb840a` — spine resume simplify + TT deepen pass (refine)  
**This session commit:** refine fast-path + fresh benchmarks (see `git log -1`)

## What you have

Integrated UCI command `gameanalysis` walks the played-move spine (FEN+moves or PGN), runs depth-D search per ply with MultiPV, grades, and streams `gameanalysis final` / `summary`.

**vs external UCI (8 threads, current binary):**

| Case | integrated_smart | uci_session | uci_fresh |
|------|------------------|-------------|-----------|
| opening_6 d10 | 90 ms (baseline) | 7.0× slower | 33× slower |
| long_20 d8 | 136 ms | 4.5× slower | 64× slower |
| opening_6_multipv3 | 198 ms | 3.1× slower | 16× slower |

**Resume modes:** `0` full ID every ply · `1` legacy (prev−1) · `2` spine (default) · `3` alias of `2` in code.

**Defaults:** `resume 2`, `resumehorizon 1`, `refine 1`, `cold 0`.

## Mechanisms (search integration)

- `startDepth` — skip shallow ID when spine reuse is safe  
- `spineContinueTt` — keep TT generation after ply 0 (subtree reuse)  
- `spineTtMinDepth` — horizon guard on shallow parent TT  
- `spinePvOrder` — root move order from parent PV tail  
- **Refine pass** — backward cheap deepen where later plies warmed TT (`deepen_nodes` in summary)

Spine policy (`resume 2`): PV rank 1 + CPL≤120 → aggressive reuse; multipv rank + CPL≤80 → mild; else `startDepth=1` + break TT gen.

## Benchmarks run this session

- Full: `scripts/benchmark_game_analysis.py` → `scripts/benchmark_results/benchmark_latest.json` + stamped `.md`
- Quick 8 min: `scripts/run_quick_experiments.py` → `scripts/benchmark_results/quick/latest.json`

**Quick sweep (resume 2/3, horizon 1):**

| Config | ~nodes vs full | opening_6 score parity vs full |
|--------|----------------|--------------------------------|
| smart_h1 (r2) | ~64% | 100% |
| merge_h1 (r3) | ~62% | 100% |
| full | 100% | — |

**PGN depth 10 (resume 2):** smart often ~48–86% nodes of full ID; legacy can be faster wall-clock but skips work (not quality-checked on long games).

## Change this session

1. **Refine skip:** if every spine ply already reached target depth, skip backward refine entirely (saves `set_position` + probes on long games).
2. **Refine walk:** reuse one `prefix` vector with `pop_back` instead of re-`assign` each ply.
3. Refreshed benchmark artifacts; tests **66/66** pass including `test_gameanalysis_parity_resume_vs_full`.

## Not done (future)

- Single `go` spanning whole game (needs Search refactor)  
- Depth-20 parity on full corpus  
- Deprecate `resume 1` / document legacy as fast-but-loose  
- PGN quality parity test (only opening_6 today)

## How to reproduce

```powershell
$env:STOCKFISH_THREADS = "8"
scripts\msys-build.sh
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" scripts\benchmark_game_analysis.py src\stockfish.exe
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" tests\instrumented.py src\stockfish.exe
```
