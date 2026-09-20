#!/usr/bin/env python3
"""vcp_remeasure.py — B-19r(VCP): re-measure VCP Coiling after the detector swap.

PRE-REGISTERED. The bands below are fixed in the commit that adds this file and
the run happens in the next one, the same order as B-97, B-94, B-92 and B-56.

── Why this has to be re-run at all ──────────────────────────────────────────
On 2026-09-19 `scan_vcp` stopped being a coarse three-window range check (are the
last three 10-day ranges each tighter than the last, >=20% overall, price above
SMA50) and started delegating to `detect_vcp_geometry`'s strict pivot walk.

B-19 (2026-09-02) measured the OLD detector: 1,951 signals, -0.59% @20d,
-1.07% @60d, sign STABLE across all four horizons in all three windows. That
reading was retired to `cache/b19_verdicts/_superseded/` because it describes a
detector that no longer ships, and the scanner went back to `unmeasured` — which
RAISED its confluence weight from 0.25 to 0.50. So the swap currently costs the
desk a known number and buys a heavier vote with nothing behind it. This run is
the only thing that settles that.

Same harness, same universe, same costs as B-19 (`walk_forward_scanner`,
LIQUID_50, 3 non-overlapping windows, IndianDeliveryCost ~29bps round trip), so
the headline number is comparable to the retired one on its own terms.

── The tier bands, fixed now ─────────────────────────────────────────────────
Mirrors how `opportunity_hub` actually assigns weight, so the verdict maps onto
a code change rather than onto an adjective:

  MEASURED (weight 1.00)  positive pooled OOS edge at BOTH 20d and 60d, sign
                          stable across all 3 windows at both, and at least one
                          window-horizon among the two flagged `reliable`
                          (the harness's own p<0.05 marker — the `*` in B-19's
                          verdict tables). Significance is per-window because
                          that is where the harness computes a t-test; the
                          pooled row is a signal-weighted average and carries
                          none.
  WEAK     (weight 0.25)  >= MIN_SIGNALS and not MEASURED — fires enough to
                          judge, does not clear the bar.
  EXCLUDE  (weight 0.00)  stable NEGATIVE at both deciding horizons with at
                          least one `reliable` window-horizon among them.
                          The VWAP Reclaim/Support precedent: a weak weight
                          still counts toward FULL_CONFLUENCE, so 0.25 is not
                          low enough for a detector measured significantly
                          negative.
  TOO FEW  (no change)    < MIN_SIGNALS pooled OOS. Stays `unmeasured`, and the
                          0.50 weight stays unearned rather than being dressed
                          up either way.

── The readout that decides it, and the one that must NOT ────────────────────
PRIMARY: forward edge, close-to-close from the signal bar, net costs. This is
the statistic B-19 used, and using anything else would make "better or worse
than the old detector" unanswerable.

SECONDARY, reported and explicitly barred from the tier decision: the
R-simulation. `backtest._simulate_plan` walks forward from the signal bar
assuming the position is ALREADY OPEN at the plan's entry price. For this
scanner that is wrong on most hits: ~80% of them are WATCH (measured 2026-09-19:
63 WATCH / 7 WEAK BUY / 6 READY / 3 BUY on 110 names x 3 cuts), and a WATCH hit's
`entry` is the PIVOT — a trigger ABOVE the current close that may never be
reached. The simulator would book a full stop-out on a trade that was never
triggered. Its R figure is therefore descriptive only, and no tier moves on it.

── What this run will NOT be allowed to mean ─────────────────────────────────
**A better number than -0.59%/-1.07% will not mean the detector improved.** The
two hit sets barely overlap — 13 old-only, 16 shared, 63 new-only on 110 names;
1,570 -> 4,201 hits in the plan census. This is a different population, not the
same population measured better, so the comparison to the retired figure is
CONTEXT and never a paired test. The same bar applies in reverse: a worse number
does not prove the old gates were better, only that this detector is not good.

**A pass will not make the 0.50 weight retroactively correct.** It was unearned
between the swap and this run either way; that is a fact about the ordering, not
something a good result erases.

CLI:
    py -3 tools/vcp_remeasure.py              # the run
    py -3 tools/vcp_remeasure.py --windows 3  # as pre-registered (default)
"""
from __future__ import annotations

import argparse
import io
import sys

#: Pooled OOS signals below which no tier moves. B-19 called three scanners
#: TOO FEW SIGNALS at single digits; 100 is the floor at which a per-window
#: sign is worth reading at all.
MIN_SIGNALS = 100

#: The two horizons the bands are written on. B-19 reported 5/10/20/60; the
#: tier decision uses the two longer ones, where the cost model has stopped
#: dominating the signal.
DECIDING = (20, 60)

#: The retired detector's reading, for context in the printout only.
OLD = {"signals": 1951, 20: -0.59, 60: -1.07, "stability": "STABLE negative"}

MEASURED, WEAK, EXCLUDE, TOO_FEW = "MEASURED", "WEAK", "EXCLUDE", "TOO FEW SIGNALS"


def classify(pooled: dict, per_window: dict, reliable: dict,
             n_signals: int) -> tuple[str, list[str]]:
    """Apply the pre-registered bands. Returns (verdict, reasons).

    `pooled`     {horizon: pooled_edge_pct}
    `per_window` {horizon: [edge_pct per window]}
    `reliable`   {horizon: [bool per window]} — the harness's own p<0.05 flag
    """
    why: list[str] = []
    if n_signals < MIN_SIGNALS:
        return TOO_FEW, [f"{n_signals} pooled OOS signals < {MIN_SIGNALS}"]

    edges = {h: pooled.get(h) for h in DECIDING}
    if any(edges[h] is None for h in DECIDING):
        return TOO_FEW, [f"no pooled edge at {DECIDING}"]

    def _stable(h, sign: int) -> bool:
        ws = per_window.get(h) or []
        return bool(ws) and all((w > 0) == (sign > 0) for w in ws)

    any_reliable = any(any(reliable.get(h) or []) for h in DECIDING)
    all_pos = all(edges[h] > 0 for h in DECIDING)
    all_neg = all(edges[h] < 0 for h in DECIDING)
    stable_pos = all_pos and all(_stable(h, +1) for h in DECIDING)
    stable_neg = all_neg and all(_stable(h, -1) for h in DECIDING)

    for h in DECIDING:
        ws = [round(w, 2) for w in (per_window.get(h) or [])]
        marks = "".join("*" if r else "." for r in (reliable.get(h) or []))
        why.append(f"@{h}d pooled {edges[h]:+.2f}%  windows {ws}  sig[{marks}]")

    if stable_pos and any_reliable:
        why.append("positive, sign-stable at both deciding horizons, and significant")
        return MEASURED, why
    if stable_neg and any_reliable:
        why.append("negative, sign-stable at both deciding horizons, and significant")
        return EXCLUDE, why
    if stable_pos or stable_neg:
        why.append("sign-stable but no window-horizon reached p<0.05")
    why.append("fires enough to judge; does not clear the positive-stable-significant bar")
    return WEAK, why


def _utf8_stdout() -> None:
    """Rewrap stdout for the box-drawing characters in the printout.

    Inside `main()`, not at import: doing it at module scope replaces the stream
    pytest has already swapped in for capture, and every test in the file then
    dies with "I/O operation on closed file" — which is how this module first
    failed, before it had run anything at all.
    """
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    _utf8_stdout()
    ap = argparse.ArgumentParser(description="B-19r(VCP) — re-measure after the swap")
    ap.add_argument("--windows", type=int, default=3)
    ap.add_argument("--symbols", type=int, default=0,
                    help="cap the universe (0 = all of LIQUID_50, as B-19 ran it)")
    args = ap.parse_args()

    import screener_pipeline as sp
    from backtest import LIQUID_50, COST_INDIAN, walk_forward_scanner

    syms = LIQUID_50[:args.symbols] if args.symbols else list(LIQUID_50)
    print(f"B-19r(VCP) — 'VCP Coiling', {len(syms)} symbols, "
          f"{args.windows} walk-forward windows, Indian delivery costs.")
    print(f"Retired detector, for context only: {OLD['signals']} signals, "
          f"{OLD[20]:+.2f}% @20d, {OLD[60]:+.2f}% @60d ({OLD['stability']}).")
    print("Different hit set — context, never a paired comparison.\n")

    cache: dict = {}

    def fetch(sym):
        if sym not in cache:
            try:
                cache[sym] = sp.fetch_ohlcv(sym, days=1500)
            except Exception:
                cache[sym] = None
        return cache[sym]

    res = walk_forward_scanner("VCP Coiling", syms, fetch,
                               n_windows=args.windows, cost_model=COST_INDIAN)

    # Real harness shape (read from backtest.py before this file was committed):
    #   res["pooled"]["horizons"][h]["edge"]              — pooled OOS edge
    #   res["pooled"]["n_signals"]                        — pooled signal count
    #   res["stability"]["per_horizon"][h]["window_edges"]— per-window edges
    #   res["windows"][i]["horizons"][h]["edge_ttest"]["reliable"] — p<0.05
    pooled_h = (res.get("pooled") or {}).get("horizons") or {}
    stab = (res.get("stability") or {}).get("per_horizon") or {}
    windows = res.get("windows") or []

    pooled: dict = {}
    per_window: dict = {}
    reliable: dict = {}
    for h in DECIDING:
        m = pooled_h.get(h) or pooled_h.get(str(h)) or {}
        pooled[h] = m.get("edge")
        sh = stab.get(h) or stab.get(str(h)) or {}
        per_window[h] = list(sh.get("window_edges") or [])
        flags = []
        for w in windows:
            wh = (w.get("horizons") or {}).get(h) or (w.get("horizons") or {}).get(str(h)) or {}
            flags.append(bool((wh.get("edge_ttest") or {}).get("reliable")))
        reliable[h] = flags

    n_signals = int((res.get("pooled") or {}).get("n_signals", 0))
    verdict, why = classify(pooled, per_window, reliable, n_signals)

    print(f"pooled OOS signals: {n_signals}")
    for line in why:
        print(f"  {line}")
    print(f"\nVERDICT (pre-registered bands): {verdict}")
    print({
        MEASURED: "-> add 'VCP Coiling' to opportunity_hub.MEASURED_EDGE_SCANNERS (weight 1.00)",
        WEAK:     "-> add 'VCP Coiling' back to MEASURED_WEAK_SCANNERS (weight 0.25)",
        EXCLUDE:  "-> add 'VCP Coiling' to PIPELINE_EXCLUDED (weight 0.00)",
        TOO_FEW:  "-> no change; it stays `unmeasured` at 0.50, still unearned",
    }[verdict])
    print("\nThe R-simulation is NOT part of this verdict — see the module "
          "docstring: ~80% of hits are WATCH, whose entry is a pivot that may "
          "never have been reached.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
