---
title: "Policy Event Study — Result: Budgets re-sort sectors, MPC days are ordinary"
category: analysis
tags: [event-study, b-184, rbi, mpc, budget, sector-indices, result, calibration, macro]
created: 2026-10-26
updated: 2026-10-26
sources: 0
related: [analyses/Policy-Event-Study-Pre-Registration, analyses/Open-Backlog, analyses/Sector-Rotation-Tool-Architecture]
---

# Policy Event Study — Result (B-184)

Run as pre-registered on [[analyses/Policy-Event-Study-Pre-Registration]], which
was committed at `ab1d9cd` before any real-data run. Code: `tools/event_study.py`
and `tools/event_study_run.py`. Full output:
`output/event_study/2026-10-26_mpc_budget.{md,json}`. Sample: 2010-01-05 to
2026-10-26. Null A used 10,000 draws at seed 7.

## Thesis

Do RBI MPC decision days and Union Budget days move NIFTY and the NSE sector
indices more than ordinary days? On MPC cut and hike days, do the rate-sensitive
sectors move the way the textbook says?

## Verdicts (as printed by `run_study`, not re-interpreted)

- **PROMOTE: budget policy days are volatility events (P2 ratio 1.65x)**
- **CALIBRATION: mpc magnitude - no promotable effect**
- **CALIBRATION: mpc directional - no promotable effect**

## Evidence

### Primary (Holm, family α 0.05)

| test | set | n | real | null mean | ratio | p | Holm p | 90 % CI |
|---|---|--:|--:|--:|--:|--:|--:|---|
| P1 \|NIFTY\| | budget | 19 | 1.06 % | 0.78 % | 1.35× | 0.101 | 0.302 | 0.69–1.53 % |
| **P2 sector dispersion** | **budget** | 18 | **1.51 %** | 0.92 % | **1.65×** | 0.0002 | **0.0008** | 1.37–1.66 % |
| P1 \|NIFTY\| | mpc | 59 | 0.68 % | 0.66 % | 1.03× | 0.364 | 0.728 | 0.54–0.83 % |
| P2 sector dispersion | mpc | 59 | 0.82 % | 0.87 % | 0.94× | 0.831 | 0.831 | 0.75–0.90 % |

### Split half: the Budget P2 result holds in both halves

| test | set | before 2019 (n, ratio, p) | from 2019 (n, ratio, p) |
|---|---|---|---|
| P2 | budget | 8 · 1.49× · 0.003 | 10 · 1.76× · 0.0008 |
| P1 | budget | 9 · 1.23× · 0.19 | 10 · 1.43× · 0.13 |
| P1 / P2 | mpc | 14 · 1.11× / 0.95× · 0.31 / 0.60 | 45 · 1.00× / 0.94× · 0.45 / 0.81 |

**Sensitivity check:** with β = 1 (sector minus NIFTY), Budget dispersion is 1.74×
(p 0.0001). The result does not depend on the market model.

### Secondary: MPC direction (raw p; buckets of 11 cuts and 8 hikes)

| test | real | p |
|---|--:|--:|
| S1 cut → basket AR > 0 | +0.00 % | 0.51 |
| S2 hike → basket AR < 0 | **+0.12 %** (wrong sign) | 0.71 |
| S3 cut − hike > 0 (label permutation) | −0.12 % | 0.71 |

The rate-sensitive basket (Bank, PSU Bank, Realty, Auto, Fin Services) shows no
decision-day reaction in either direction. Hike days were, if anything, slightly
positive for it.

## Evidence against / limitations

- **Small samples.** There are 19 budgets and 8–11 events per MPC bucket. The
  Budget P1 ratio of 1.35× may be a real effect that this sample is too small to
  confirm. A ~1.35× effect with n = 19 is under-powered, so P1 is **not
  established, not refuted**.
- **Decision, not surprise.** The MPC label is the decision, not the surprise.
  A decision the market expected is priced in beforehand. This null says that
  *decision days* are ordinary. It does not say that *surprises* are. The three
  unscheduled moves (two COVID cuts in 2020, the May-2022 hike) are the
  closest thing to surprises. Only the 2022 hike moved NIFTY much (|r| 2.3 %),
  with n = 3 and untested.
- **Single-source rows.** 8 of the 81 rows rest on a single source. All of them
  are MPC rows, and none is a budget, so the promoted result is unaffected.
- **Two data repairs, both found during the run** (`patch_sessions`):
  - **2014-02-17.** Yahoo has Bank Nifty but no NIFTY on that day. On the first
    run the event was snapped to the next session. That two-session return
    inflated Budget P1 from 1.35× to 1.41×, exactly the bias the pre-registration
    warned about.
  - **Sat 2025-02-01.** Yahoo has NIFTY but no sector index, so that budget had
    silently dropped out of P2.
  - Both are now restored from NSE files, and the run above is after both fixes.
    Neither fix changed a verdict.

## Exploratory (no claims; BH q within set)

Where the Budget dispersion comes from on day 0:

| index | statistic | budget-day mean | q |
|---|---|--:|--:|
| FMCG | \|AR\| | 1.34 % vs 0.59 % normal (2.3×) | 0.008 |
| PSE | AR (down) | **−1.01 %** | 0.008 |
| Energy | AR (down) | −0.72 % | 0.026 |
| Infra | AR (down) | −0.43 % | 0.039 |
| PSU Bank / Realty / Fin Services | \|AR\| | ~1.6–1.9× normal | 0.09 |

A pattern worth a pre-registered test, not a claim: **state-linked sectors (PSE,
Energy, Infra) have underperformed NIFTY on budget day itself**. One reading is
that capex announcements are anticipated, so the stocks are bought on the
rumour and sold on the news. Pharma's post-window (+1 to +5) drift of +2.0 %
(q 0.12) is not significant.

## Conclusion

- **Budget day is a sector-rotation day, not (provably) a market-direction day.**
  Sectors scatter about 1.65× more than on a normal day, consistently across
  2011–2026. NIFTY's own move is only possibly larger.
- **MPC decision days are ordinary days** for NIFTY, for sector dispersion and for
  the rate-sensitive basket. The market prices RBI decisions before they are
  announced.

## Action taken / plan

- **Earned by the decision rule:** a desk context flag along the lines of
  "Budget day — expect sector dispersion ~1.6× normal; size sector bets
  accordingly". Not built in this change: it needs a calendar surface (the
  catalyst-calendar idea), which is a separate piece of work.
- **No MPC flag.** Showing "RBI day" as a risk badge would be decoration. If it is
  displayed at all, it must not be presented as a volatility warning.
- **Possible follow-ups:**
  - Pre-register the state-linked-sector budget-day fade (PSE, Energy, Infra) with
    a fresh sample period or out-of-sample check.
  - An MPC *surprise* study, which needs consensus or OIS (overnight index swap)
    expectations data the desk does not have.

## Outcome (fill in later)

## Related Pages

- [[analyses/Policy-Event-Study-Pre-Registration]]: hypotheses, data, the
  decision rule and the priors. The prior for Budget P1 was "likely PROMOTE"; it
  came out short of significance. The P2 and MPC priors were borne out.
- [[analyses/Open-Backlog]]: B-184
- [[analyses/Sector-Rotation-Tool-Architecture]]: where a budget-day dispersion
  note could live
