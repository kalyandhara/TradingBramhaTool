# SBC Vedha Backtest — ^NSEBANK

- Window: +/-2 trading days · severity>=1.0 · anchor=natal (Purva Bhadrapada)
- Sample: 2007-09-17..2026-08-18 (4652 days)
- Vedha days: 827 (17.8%); eclipse-adjacent: 408
- Null: 5000 circular rotations · OR uses Haldane-Anscombe correction

| label | set | vedha_days | coverage | recall | **lift** | null_lift | p | odds_ratio |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| fractal_k5 | full | 827 | 54.1% | 52.2% | **0.97x** | 1.00x | 0.797 | 0.91 |
| fractal_k5 | no-eclipse | 755 | 54.1% | 52.2% | **0.96x** | 1.00x | 0.769 | 0.91 |
| fractal_k10 | full | 827 | 30.2% | 31.0% | **1.02x** | 1.00x | 0.380 | 1.05 |
| fractal_k10 | no-eclipse | 755 | 30.2% | 32.8% | **1.09x** | 1.00x | 0.136 | 1.16 |
| voljump_p95 | full | 827 | 22.8% | 26.1% | **1.15x** | 1.00x | 0.133 | 1.25 |
| voljump_p95 | no-eclipse | 755 | 22.8% | 27.4% | **1.20x** | 1.00x | 0.071 | 1.35 |

## Decision rule (pre-registered)
Promote to a watch-window ONLY if, out-of-sample: lift >= 1.3 AND p < 0.01 AND it survives eclipse-stripping AND holds across >=2 label defs and >=2 instruments. A lift ~1.0 with p>0.1 is a clean negative — that is a valid, useful result. Direction is NOT tested here and is not implied. Educational, not investment advice.

