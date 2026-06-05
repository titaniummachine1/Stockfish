# Game-analysis audit

**Branch:** `feature/game-analysis-poc`

## Governing rule

**First, do no harm** — then improve. Speed ideas must pass `strict 1` quality CI @ 1 thread before changing defaults.

## Modes (`gameanalysis summary … mode … startdepth …`)

| Flag | Summary `mode` | Meaning |
|------|----------------|---------|
| `strict 1` | `parity` | Full 1..D ID every ply; **resume shortcuts disabled**; matches `resume 0` scores @ 1 thread |
| `strict 0` + `resume 2` | `resume` | Speed path: `startDepth` skip, `spinePvOrder`, TT breaks on off-PV |
| `resume 0` | `full` | Reference spine (full ID, no resume policy) |

`startdepth` in summary = max `startDepth` used on forward spine (1 = full ladder every ply).

**Defaults:** `resume 2`, `refine 1`, `strict 0`, `cold 0`.

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
- Speed only: frontier aspiration widen when `startDepth > 1` and not strict

## Benchmarks (8 threads, latest)

See [`scripts/benchmark_results/benchmark_latest.md`](../scripts/benchmark_results/benchmark_latest.md).

| Mode | Role |
|------|------|
| `integrated_full_id` | Reference |
| `integrated_parity` | Correctness (`strict 1`) |
| `integrated_smart` | Speed (`strict 0`) — **not** same eval as full ID |
| `uci_session` | External per-ply baseline |

Example `opening_6` d10: parity 269 ms; smart 134 ms (~2× faster, ~55% nodes); uci_session 628 ms.

## Gated experiments (@ 1 thread, 3 min)

| Config | Nodes vs full | Quality |
|--------|---------------|---------|
| `parity_h1` (r2 strict 1) | ~100% | 100% |
| `smart_h1` (r2 strict 0) | ~79% | 100% on opening_6 only* |

\*Quality CI uses strict 1; smart mode is not score-gated in CI.

## Out of scope

- Backward propagation changing per-ply eval meaning
- Virtual TT / aspiration Strategy 1
- Default `strict 1`
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
