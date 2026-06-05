# Game-analysis experiments (minimal)

## Rule

First do no harm (`strict 1` CI), then improve (`strict 0` resume).

## Modes

- `strict 1` — parity: full 1..D ID, no resume shortcuts (see `exp/AUDIT.md`)
- `strict 0` — speed: resume 2, startDepth skip, spinePvOrder

## Quick @ 1 thread (2026-06-05)

| config | nodes vs full |
|--------|---------------|
| parity_h1 | 100% |
| smart_h1 | 79% |

Full audit: `exp/AUDIT.md`
