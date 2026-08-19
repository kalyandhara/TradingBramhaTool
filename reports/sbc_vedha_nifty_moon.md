# SBC Vedha Backtest — ^NSEI

- Window: +/-2 trading days · severity>=1.0 · anchor=moon ((transit Moon))
- Sample: 2007-09-17..2026-08-18 (4640 days)
- Vedha days: 728 (15.7%); eclipse-adjacent: 401
- Null: 5000 circular rotations · OR uses Haldane-Anscombe correction

| label | set | vedha_days | coverage | recall | **lift** | null_lift | p | odds_ratio |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| fractal_k5 | full | 728 | 53.9% | 52.3% | **0.97x** | 1.00x | 0.826 | 0.93 |
| fractal_k5 | no-eclipse | 644 | 53.9% | 53.9% | **1.00x** | 1.00x | 0.539 | 1.00 |
| fractal_k10 | full | 728 | 29.7% | 29.4% | **0.99x** | 1.00x | 0.591 | 0.98 |
| fractal_k10 | no-eclipse | 644 | 29.7% | 30.7% | **1.04x** | 1.00x | 0.288 | 1.06 |
| voljump_p95 | full | 728 | 23.8% | 22.7% | **0.95x** | 1.00x | 0.799 | 0.93 |
| voljump_p95 | no-eclipse | 644 | 23.8% | 23.1% | **0.97x** | 1.00x | 0.678 | 0.96 |

## Decision rule (pre-registered)
Promote to a watch-window ONLY if, out-of-sample: lift >= 1.3 AND p < 0.01 AND it survives eclipse-stripping AND holds across >=2 label defs and >=2 instruments. A lift ~1.0 with p>0.1 is a clean negative — that is a valid, useful result. Direction is NOT tested here and is not implied. Educational, not investment advice.

