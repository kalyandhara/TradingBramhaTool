# SBC Vedha Backtest — ^NSEI

- Window: +/-2 trading days · severity>=1.0 · anchor=natal (Purva Bhadrapada)
- Sample: 2007-09-17..2026-08-18 (4640 days)
- Vedha days: 827 (17.8%); eclipse-adjacent: 401
- Null: 5000 circular rotations · OR uses Haldane-Anscombe correction

| label | set | vedha_days | coverage | recall | **lift** | null_lift | p | odds_ratio |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| fractal_k5 | full | 827 | 53.9% | 54.1% | **1.00x** | 1.00x | 0.478 | 1.01 |
| fractal_k5 | no-eclipse | 755 | 53.9% | 53.5% | **0.99x** | 1.00x | 0.550 | 0.98 |
| fractal_k10 | full | 827 | 29.7% | 28.8% | **0.97x** | 1.00x | 0.676 | 0.95 |
| fractal_k10 | no-eclipse | 755 | 29.7% | 28.6% | **0.96x** | 1.00x | 0.683 | 0.94 |
| voljump_p95 | full | 827 | 23.8% | 25.2% | **1.06x** | 1.00x | 0.329 | 1.10 |
| voljump_p95 | no-eclipse | 755 | 23.8% | 26.4% | **1.11x** | 1.00x | 0.214 | 1.18 |

## Decision rule (pre-registered)
Promote to a watch-window ONLY if, out-of-sample: lift >= 1.3 AND p < 0.01 AND it survives eclipse-stripping AND holds across >=2 label defs and >=2 instruments. A lift ~1.0 with p>0.1 is a clean negative — that is a valid, useful result. Direction is NOT tested here and is not implied. Educational, not investment advice.

