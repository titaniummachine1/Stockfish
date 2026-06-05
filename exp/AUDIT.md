# Game-analysis audit

**Branch:** `feature/game-analysis-poc`

## Governing rule

**First, do no harm** — then improve. Speed ideas must pass `strict 1` quality CI @ 1 thread before changing defaults.

## Modes (`gameanalysis summary … mode … startdepth …`)

| Flag | Summary `mode` | Meaning |
|------|----------------|---------|
| `strict 1` | `parity` | Full 1..D ID every ply; **resume shortcuts disabled**; matches `resume 0` scores @ 1 thread |
| `strict 0` + `resume 2` | `resume` | Speed: parent-policy `startDepth`, TT cap, `spinePvOrder` |
| `strict 0` + `resume 3` | `resume` | Speed: merge — TT-primary skip + policy gates (default) |
| `resume 0` | `full` | Reference spine (full ID, no resume policy) |

`startdepth` in summary = max `startDepth` used on forward spine (1 = full ladder every ply).

**Defaults:** `resume 3` (merge), `refine 1`, `strict 0`, `cold 0`.

Hosts needing depth-D parity: `gameanalysis depth D … strict 1` (optional `resume 2` — ignored for search path when strict).

## Quality contract (CI)

```bash
export STOCKFISH_THREADS=1
python scripts/gameanalysis_quality.py src/stockfish.exe
```

- Reference: `resume 0 refine 0`
- Candidate: `resume 2 refine 1 strict 1`
- Hard gates: `depth >= D`, score kind, best move, full score string

**67/67** instrumented tests including `test_gameanalysis_quality_contract_benchmark_cases`.

## Search hooks

- `LimitsType.spineStrictParity` — forces `startDepth = 1` in [`search.cpp`](../src/search.cpp)
- `strict 1` in gameanalysis — disables `useResume` (no skip, no `spinePvOrder`)
- **TT cap:** probe `spine_tt_depth()` at child before `go`; `startDepth ≤ ttDepth+1` (not blind `parent−1`)
- **Virtual aspiration ladder:** replay TT scores for depths `1..startDepth−1` (zero nodes) before frontier search
- **Frontier aspiration:** wide window if TT did not seed; `2× delta` if virtual ladder filled

## Benchmarks (8 threads, latest)

See [`scripts/benchmark_results/benchmark_latest.md`](../scripts/benchmark_results/benchmark_latest.md).

| Mode | Role |
|------|------|
| `integrated_full_id` | Reference |
| `integrated_parity` | Correctness (`strict 1`) |
| `integrated_merge` | Default speed (`resume 3`) |
| `integrated_smart` | `resume 2` speed variant |
| `uci_session` | External per-ply baseline |

PGN depth 10 vs `uci_session`: **1.3–2.5×** wall (merge); **~20–35%** fewer nodes on long games.  
Still **~89 separate `go` calls** per game — major ceiling until single-spine `Search` refactor.

## Gated experiments (@ 1 thread, 3 min)

| Config | Nodes vs full | Quality |
|--------|---------------|---------|
| `parity_h1` (r2 strict 1) | ~100% | 100% |
| `smart_h1` (r2 strict 0) | ~79% | 100% on opening_6 only* |

\*Quality CI uses strict 1; smart mode is not score-gated in CI.

## Out of scope (next big wins)

- Single internal `go` / spine walk inside `Search` (drop per-ply thread sync)
- TT-exact ply skip (`BOUND_EXACT` + `ttDepth ≥ D`) without full root search
- Default `strict 1` for hosts needing depth-D parity without flag
- Elo

## Reproduce

```powershell
scripts\msys-build.sh
$env:STOCKFISH_THREADS="1"
python scripts\gameanalysis_quality.py src\stockfish.exe
python tests\instrumented.py src\stockfish.exe
$env:STOCKFISH_THREADS="8"
python scripts\benchmark_game_analysis.py src\stockfish.exe
```
