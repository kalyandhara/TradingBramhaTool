---
title: "Sweep Card, Full Window (B-186d) — Result: positive on both panels, established on neither"
category: analysis
tags: [b-186d, liquidity-sweep, chart-tour, base-rate, result]
created: 2026-10-27
updated: 2026-10-27
sources: 0
related: [analyses/Sweep-Full-Window-Pre-Registration, analyses/Sweep-Reconciliation-Result, analyses/Chart-Tour-Base-Rates-Result, analyses/Open-Backlog]
---

# Sweep Card, Full Window (B-186d) — Result

Run as pre-registered on [[analyses/Sweep-Full-Window-Pre-Registration]] (`48560ea`). The
script is `tools/sweep_full_window_study.py`, committed at `470926f` before the run. Output:
`tools/cache/sweep_full_window.json`.

## Thesis

With the 260-bar limit removed, does the tour's bullish liquidity sweep card carry
information on a panel it has never seen?

## Result

| Panel | Role | Events | Names | mean20 | p | Bonferroni p | Thirds | Label |
|---|---|---|---|---|---|---|---|---|
| `nifty500[300:500]` | **decides** (unseen) | 3,240 | 171 | **+0.34 %** | 0.35 | 1.0 | + − − | **ORDINARY** |
| `nifty500[:300]` | reported (seen in B-186a S5) | 5,119 | 257 | +0.48 % | 0.10 | 1.0 | + − − | ORDINARY |

The main-panel figures match reconciliation step S5 exactly, which confirms the code path.

## Conclusion

- **The card is ORDINARY with a full window as well.** Both panels give a positive sign
  (+0.34 %, +0.48 %), which is roughly what B-41m found, but neither comes near significance
  at the per-symbol level. The thirds read + − −: the gain sits in the earliest third of the
  750 bars, the same pattern most ordinary cards showed.
- **B-41m's +0.51 % stands as a LIQUID_50 result.** It is significant when signals are
  pooled over 50 large caps (S1–S3), but it does not reach significance across the wider
  NIFTY 500 over the last three years.
- **The tour card was not hiding an edge.** The 260-bar window had turned a weak positive
  into a weak negative, and correcting it brings back the weak positive. That is what the
  card now shows.

## Action taken (as pre-registered)

1. **Live tour:** the sweep card now sees the full history (`chart_tour.FULL_HISTORY`), and
   so does the monthly base-rate replay (`tour_base_rates.detector_events`), so a refresh
   cannot quietly undo the change. The reconciliation ladder opts out, so its S6 stays at
   260 bars. Commit `9cc866d`.
2. **Badge:** the `liquidity_sweep_bull` entry in `tour_base_rates.json` is replaced with
   the full-window main-panel numbers (+0.48 %, ORDINARY), `confirm_label` ORDINARY and
   `window: full history (B-186d)`.

   **Ruling (a deviation from the pre-registration's wording):** `confirmed` is **null**,
   not false. That follows the tour's existing `merge_confirmation`, where only an
   EDGE/INVERTED card can be confirmed or not. A false here would have made an Ordinary card
   display "not confirmed on a fresh panel". Cost if wrong: a flag's wording only.
3. No other card changed.

**Still open:** whether the other pool- or swing-based desk cards (structure break, AB=CD,
flag) are also clipped by the 260-bar window. That is not tested here.

## Outcome (fill in later)

## Related Pages

- [[analyses/Sweep-Full-Window-Pre-Registration]]
- [[analyses/Sweep-Reconciliation-Result]]: why the window mattered
- [[analyses/Chart-Tour-Base-Rates-Result]]
- [[analyses/Open-Backlog]]: B-186d
