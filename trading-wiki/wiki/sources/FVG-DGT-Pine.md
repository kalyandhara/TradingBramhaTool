---
title: "TradingView — Fair Value Gaps by DGT"
category: source
tags: [pine-script, fvg, fair-value-gap, dgt, dgtrd, imbalance, mitigation, fill-classification, mtf, htf, ltf, intrabar, ict, tradingview]
created: 2026-07-22
updated: 2026-07-22
sources: 1
related: [entities/DGT, concepts/Fair-Value-Gap, concepts/Multi-Timeframe-Analysis, sources/FVG-LuxAlgo-Pine, sources/LuxAlgo-Smart-Money-Concepts-Pine, sources/BOS-FVG-Pullback-Signals-Pine]
---

# TradingView — Fair Value Gaps by DGT

## Metadata
- Author: © **dgtrd** ([[entities/DGT]]), TradingView Pine Wizard
- Source: https://www.tradingview.com/script/Onab2fvE-Fair-Value-Gaps-by-DGT/
- License: open-source (public TradingView script; verify exact terms on the script page before any port)
- Format: TradingView Pine Script overlay indicator
- Ingested: 2026-07-22 (URL fetch)

## Why this matters
The third FVG indicator ingested this session, and it contributes two things neither the [[sources/FVG-LuxAlgo-Pine|LuxAlgo standalone]] nor the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|SMC superset]] nor the [[sources/BOS-FVG-Pullback-Signals-Pine|Quant]] script expose:
1. **Fill/mitigation is a user choice with four explicit definitions** — this *parameterizes* the wick-through-vs-close-through mitigation contradiction the wiki has tracked on [[concepts/Fair-Value-Gap]] instead of hard-coding one side.
2. **Three-source detection incl. LTF/intrabar** — LuxAlgo projects gaps *down* from a higher timeframe; DGT also detects gaps on a *lower* timeframe (intrabar), auto-selecting the LTF from chart resolution. That surfaces imbalances hidden inside the current bar.

## Key Takeaways
1. **Four fill-classification definitions (the standout).** A gap counts as "filled" per the user's chosen rule:
   - **Any Touch** — price merely reaches the near edge (most aggressive; ≈ LuxAlgo's wick-through retire-on-touch).
   - **Midpoint Reached** — price trades to the 50% level (the FVG midpoint = the "consequent encroachment" level ICT traders watch; also the Fib-0.5 continuation entry noted on [[concepts/Fair-Value-Gap]]).
   - **Wick Sweep** — a wick fully crosses the gap.
   - **Body Beyond** — a *body/close* pushes fully through (most conservative; ≈ the Quant script's close-through invalidation).
   This turns the mitigation-rule debate into a dial: Any Touch and Body Beyond are the two ends of the wiki's existing contradiction.
2. **Live fill % per gap.** Real-time completion percentage as price repairs each imbalance — same quantitative intent as the LuxAlgo standalone's dashboard, but per-gap and continuous.
3. **Three-source MTF: current TF + HTF + LTF/intrabar.** "Auto" picks the optimal lower timeframe from chart resolution. HTF = context/bias imbalances projected onto the chart; LTF/intrabar = imbalances hidden inside the current bar. See [[concepts/Multi-Timeframe-Analysis]].
4. **Lifecycle states tracked continuously:** unfilled → partially repaired → fully resolved. Partial-repair tracking (not just filled/unfilled) matches the "partial fill = the entry" lifecycle from the Quant script.
5. **UX: toggleable labels + hover tooltips on the FVG midpoint** for persistent per-gap detail without chart clutter.
6. **ICT framing.** Explicitly positioned in Inner Circle Trader / market-structure / MTF terms (imbalance, liquidity displacement).

## Detailed Notes
- Detection primitive is the standard 3-candle non-overlap gap; the differentiation is entirely in **classification (fill logic)** and **detection source (which timeframe the gap is read from)**, not in the raw gap definition.
- The **midpoint** is treated as a first-class level here (both a fill definition and the tooltip anchor) — consistent with the wiki's note that the FVG midpoint ≈ Fib 0.50 = the cleanest continuation entry.

## Actionable Insights
- **Port target for `tools/fvg.js`:** expose fill logic as a **mode parameter** (`any_touch | midpoint | wick_sweep | body_beyond`) rather than hard-coding one mitigation rule. This is the clean way to resolve the wiki's standing wick-vs-close contradiction in code — let the caller pick per use case (visualizer → Any Touch; entry-signal engine → Body Beyond). Fits FF-2 in [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]].
- **LTF/intrabar detection** is a new capability for this project's chart stack (we only project HTF context today) — lower priority, but noted.

## Contradictions with Existing Wiki
No new contradiction — instead a **resolution mechanism** for the existing one. The [[concepts/Fair-Value-Gap]] page carries a contradiction between LuxAlgo's wick-through mitigation and the Quant script's close-through invalidation. DGT's four fill definitions show both are valid endpoints of one configurable spectrum (Any Touch ↔ Body Beyond), which is how the code should model it.

## Pages Updated
- [[concepts/Fair-Value-Gap]] — added DGT variant (four fill definitions as a mitigation-rule spectrum; LTF/intrabar detection; live fill %).
- [[entities/DGT]] — new author entity.
