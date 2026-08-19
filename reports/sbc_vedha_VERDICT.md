# SBC Vedha Backtest — Verdict (2026-08-17)

**Question:** do SBC *daily* geometric vedhas onto the index anchor nakshatra mark
real NIFTY turning points better than chance?

**Answer: No. Clean negative. Do not promote.**

Pipeline: `tools/sbc_vedha_backtest.py` (reuses `sbc_scoring.cast_vedas` +
`sbc_grid` geometric vedha). Signal = malefic vedha weight >= 1.0 onto the anchor;
window +/-2 trading days; null = 5,000 structure-preserving circular rotations;
eclipse-adjacent control on. Turn labels: fractal k=5, fractal k=10, voljump p95.

| Run (2007-09 .. 2026-08, ~4,640 days) | lift range | p range | report |
|---|---|---|---|
| ^NSEI, natal anchor (Purva Bhadrapada) | 0.96–1.11x | 0.21–0.68 | `sbc_vedha_nifty.md` |
| ^NSEI, Moon anchor (natal-free) | 0.95–1.04x | 0.29–0.83 | `sbc_vedha_nifty_moon.md` |
| ^NSEBANK, natal anchor | 0.96–1.20x | 0.07–0.80 | `sbc_vedha_nsebank.md` |

Pre-registered pass bar: **lift >= 1.3 AND p < 0.01 AND survives eclipse-strip AND
holds across >=2 label defs AND >=2 instruments.** Nothing clears it.

- Lift sits at chance (~1.0) everywhere.
- The best single cell (^NSEBANK voljump no-eclipse: 1.20x, p 0.071) is under the
  bar and does NOT replicate on ^NSEI (1.11x, p 0.21) — non-replicating best-of-many
  looks, i.e. noise.
- Eclipse-stripping barely changed anything: no eclipse effect was present to remove.

**Honest stop:** chasing the 1.20x cell with more parameter sweeps would be p-hacking
against the pre-registered rule. The prior is retired with evidence.

This tests TIMING only (turn clustering). Direction was never tested and is not
implied. Educational, not investment advice.

Reproduce:
```
py -3 tools/sbc_vedha_backtest.py --out reports/sbc_vedha_nifty.md
py -3 tools/sbc_vedha_backtest.py --anchor moon --out reports/sbc_vedha_nifty_moon.md
py -3 tools/sbc_vedha_backtest.py --symbol ^NSEBANK --out reports/sbc_vedha_nsebank.md
```
