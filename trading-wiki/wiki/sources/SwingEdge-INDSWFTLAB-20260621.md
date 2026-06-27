---
title: "SwingEdge — INDSWFTLAB Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, extended, overowned, distribution-days, relative-strength]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/INDSWFTLAB, entities/KDDL, entities/NRBBEARING, entities/AADHARHFC, concepts/Distribution-Days, concepts/Stage-Analysis, concepts/RSI]
---

# Source — SwingEdge.info Stock Detail Page (INDSWFTLAB)

## Metadata
- **Source type**: Swing-trading scanner/setup web app, same source as the 4 prior SwingEdge ingests
- **URL**: https://www.swingedge.info/stocks/INDSWFTLAB
- **Snapshot date**: 2026-06-21

## Key Takeaways
- Ind-Swift Laboratories Ltd. (Pharmaceuticals & Drugs) scored only **55/100 setup readiness** — "Extended," verdict **"Wait and Watch"** (not "Watchlist-worthy" or "Strong" like the prior 4 tickers — this is the first SwingEdge ingest with an explicitly cautionary headline verdict). Decision-quality grade B, 63/100.
- **4 skip reasons listed — the most of any ticker ingested from this source so far** (KDDL: 1, NRBBEARING: 1, AADHARHFC: 1, INDSWFTLAB: 4): extended 8% past the pivot (chasing risk), stop 10% away (too wide), 4 distribution days recently, and RSI 78 ("overheated, prone to a shakeout").
- **New risk-factor language not seen on prior tickers: "RS rank 100 — overowned (NSE: 21-25% win rate, operators distribute here)."** This is a striking explicit claim — the source is saying a *maximal* RS rank is itself a contrarian warning sign, with a cited win-rate range (21–25%) for chasing already-extended RS-100 names on the NSE specifically. This is the **opposite framing** from NRBBEARING's page, where RS 100 was presented as purely a positive ("a market leader, stronger than most NSE stocks") with no overowned caveat — worth treating RS rank as context-dependent (extended + overowned vs. fresh + leading) rather than a context-free score, per the source's own messaging.
- Tags: Stage 2, RS leader, VCP active. But unlike KDDL/NRBBEARING (where these tags accompanied genuinely strong verdicts), here they coexist with "Extended" / "Wait and Watch" — same structural tags, opposite actionability, reinforcing that the tags describe pattern *presence*, not setup *quality* or *timing*.
- **Pivot type explicitly flagged "sloppy — lower follow-through expected"** — the first ticker where the pivot quality itself (not just price levels) is called out as a weakness. Contrast with KDDL's "flat-top — premium structure" pivot from the first ingest — pivot shape/quality appears to be a real, separate scored dimension in this source's model.
- Risk distance to stop is unusually large relative to the "wrong below" framing: stop is 16.2% below current price in the invalidation panel, but only 9.8% below the stated entry (₹174.1) — because the entry zone (₹154.6–174.1) sits well below current price (extended 8% past it), so risk-from-current-price and risk-from-stated-entry diverge sharply on an already-extended name. Worth noting as a general pattern: on "Extended" verdicts, always check risk-from-current vs. risk-from-the-scanner's-stated-entry separately, since they can differ a lot.
- Sector ("Pharmaceuticals & Drugs") ranked **mid-pack, #20/32** — neither leading nor lagging, unlike the clean divergence/agreement patterns seen on the first 3 tickers. A useful third data point: sector-rank vs. stock-RS relationship isn't binary (lead/lag) — it spans a spectrum, and INDSWFTLAB sits in the unremarkable middle of it.
- 4 distribution days recently — second ticker with this flag after AADHARHFC, reinforcing that the formula from [[concepts/Distribution-Days]] (down close + vol ≥50d avg+0.5σ + wide spread + close near low) is a recurring, real signal across multiple names, not a one-off.

## Detailed Notes

**Setup snapshot (as of 2026-06-21):**
- Price: ~₹187.4
- Entry zone: ₹154.6–174.1 (below current price — the scanner's reference entry has already been passed)
- Support / stop: ₹157.0
- Resistance / pivot: ₹173.2 (price already ~8.2% above it — "Extended" status)
- Next resistance: ₹207.9; further target ₹222.6
- Risk/Reward: 2.0:1; risk ≈ ₹17.13/share from entry ₹174.1

**Bullish factors listed** (same recurring UI quirk: mixes true positives with penalties under one heading): prior pivot rejection (-8 pts, penalty); sloppy pivot type (penalty, oddly under "bullish"); RS 100 "overowned" warning (also a penalty, also under "bullish" — this source's "bullish factors" card is now confirmed across 5/5 tickers to liberally include negative-scored items); RSI 78 "hot"; higher lows; RS-elevated-but-leadership-confirmed; volume expansion; quiet accumulation.

**Why now / Why not 100**: "Volume quality is not in top confirmation range yet" + "Price is extended 8.2% above pivot zone" — the extension itself is explicitly named as a why-not-100 reason, on top of being a skip reason, on top of being in the risk-factors card — three separate places on one page flag the same underlying fact (price ran past the pivot), suggesting this is the dominant driver of the page's overall caution.

## Actionable Insights
- The "RS 100 — overowned, 21-25% win rate" framing is a genuinely new and important piece of methodology from this source — worth treating high RS rank as a *timing* signal (don't chase an already-extended RS-100 name) rather than a pure *quality* signal, separate from whether the stock itself is fundamentally/structurally sound. Cross-reference against [[concepts/RSI]] and any future SwingEdge ingest with RS 100 — check whether the page treats it as "leader, buy" (NRBBEARING) or "overowned, wait" (INDSWFTLAB) framing, since apparently the source itself distinguishes these based on extension/RSI context, not RS rank alone.
- This is now 2 of 5 SwingEdge tickers (AADHARHFC, INDSWFTLAB) with a distribution-days flag, both with similarly mixed/cautious overall verdicts (C/51 and B/63 respectively) — distribution-day presence correlates with lower decision-quality grades across this small sample so far.
- "Pivot type" quality (flat-top/premium vs. sloppy/lower-follow-through) is confirmed as a real, separate input across at least 2 tickers (KDDL positive, INDSWFTLAB negative) — worth treating as its own checklist item in any future technical screen, distinct from the existence of a pivot.

## Contradictions with Existing Wiki
- **Resolved 2026-06-22** via [[sources/SwingEdge-Learn-Trends-Stages]]: SwingEdge's own stated philosophy is "[RS] surfaces context; use it to narrow a list, not to skip your own chart read" — RS is explicitly a *filter*, not a standalone verdict. That resolves the apparent tension with Minervini's RS≥70/90s Stage-2 criterion noted below: Minervini's rule is a floor/gate for inclusion, while SwingEdge's "overowned" caveat is specifically about chasing an already-extended RS-100 name on top of passing that gate — not a contradiction, just two layers of the same filter (pass the RS gate, then still judge entry timing separately).

## Pages Updated
- Created [[entities/INDSWFTLAB]]
- This source page
