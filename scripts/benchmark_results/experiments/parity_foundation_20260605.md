# Gated speed experiments (2026-06-05)

**Rule:** strict 1 must pass quality CI before promoting speed defaults.

## Result @ 1 thread (~3 min quick sweep)

| Config | mean nodes vs full | opening_6 quality |
|--------|-------------------|-------------------|
| full | 100% | — |
| parity_h1 (resume 2, strict 1) | 100% | 100% |
| smart_h1 (resume 2, strict 0) | 79% | 100% |
| merge_h1 (resume 3, strict 0) | 79% | 100% |

**Conclusion:** `strict 1` is harmless vs full_id (parity mode). `smart_h1` saves ~21% nodes but is **not** CI-gated for full corpus score parity — use for speed only.

**Promoted:** nothing to default; keep `strict 0` default, document `strict 1` for parity hosts.
