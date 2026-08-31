---
title: "Contra Strategy Roadmap"
category: analysis
type: analysis
created: 2026-08-31
updated: 2026-08-31
tags: [contra, roadmap, value, screening, piotroski, buyback, unvalidated]
related: [concepts/Margin-Inflection-Contra, concepts/Mean-Reversion, concepts/PEAD, concepts/Market-Sentiment-Index, analyses/Open-Backlog, analyses/Noise-Regime-Coverage-Postmortem, analyses/SVP-Signal-Backtest-Design, concepts/Sarvatobhadra-Chakra]
---

# Contra Strategy Roadmap

Sequencing plan for the contra lane, built on top of [[analyses/Open-Backlog]] B-49
(value screen), B-50 (margin inflection) and B-51 (volume anomaly).

## Part 1 — the seven-strategy list, scored against this repo's own measurements

The supplied list is a reasonable taxonomy. Two of its seven entries have **already
been measured here and came back negative**, and the list rates both of those as its
strongest. That is the single most important thing to record.

| # | Strategy | Status here | Verdict |
|---|---|---|---|
| 1 | **Sentiment-extreme reversal** | `sentiment_index.py` (4-input composite), `pcr.py`, `market_health.py` — all **descriptive, none gate anything** | **Best-supported, and the biggest unrealised asset.** Already filed as B-32 |
| 2 | **Value dislocation** | **B-49 shipped** | Done; needs the F-Score guard below |
| 3 | **Liquidity exhaustion** (POC / VA / exhaustion) | `SVP.buildSignal` — **MEASURED CLEAN NEGATIVE** | See warning below |
| 4 | **Mean reversion** | `scan_mean_reversion_connors` shipped; `RSI 60-40` measured **no edge as tuned** | Built. Do not add more oscillator variants |
| 5 | **Macro cycle reversal** | nothing built | **Lowest ROI.** A handful of turning points per decade is not a testable sample |
| 6 | **Event-driven contra** | `scan_pead`, `Zero-Debt Quality PEAD`, `earnings_calendar` SUE | Built, and [[concepts/PEAD]] is the one anomaly with real Indian evidence |
| 7 | **Astro-contra (KP + SBC)** | SBC daily-vedha NIFTY backtest — **clean negative** | See warning below |

> [!warning] The list's two highest-rated methods are the two this repo has already falsified.
> It calls liquidity exhaustion *"extremely powerful when combined with your POC cluster
> analysis"* and astro-contra *"the highest-accuracy contra method in astro-quant trading."*
>
> **Neither claim survives our own data.** [[analyses/SVP-Signal-Backtest-Design]]: not
> merely no edge — **5 of 7 factor families are sign-inverted**, `corr(score, 20d fwd) =
> −0.041`, stop-and-reverse median −80%, beat buy&hold 0/8. The `trap` factor carrying the
> engine's largest weight (1.5) attributes at **−0.51**. The SBC daily-vedha study is
> likewise recorded as a clean negative.
>
> This is what a confident source with no sample size looks like. Neither should anchor a
> contra stack; the SVP engine is a **reading aid**, and the astro layer is unfalsified
> only where it has not yet been tested.

**Also worth naming:** the "Confluence Model" at the end of the list stacks Layer 1
(exhaustion) on Layer 2 (astro) on Layer 3 (price). **Two of those three layers are the
measured-negative ones.** Confluence between two negative signals is not more reliable
than either — it is the same error twice, with more conviction attached.

## Part 2 — the three screens you named

### Sales > 2× market cap  (i.e. **P/S < 0.5**)

Real and classic — the Ken Fisher *Super Stocks* screen. **But it is sector-conditional to
the point of being sector-selection in disguise:** distribution, trading and commodity
processing businesses pass permanently on structurally thin margins, and software or
pharma essentially never pass. Screening P/S absolute across a mixed universe returns a
sector list, not a value list.

**Fix:** rank P/S *within sector* (yfinance `.info` supplies `sector` free, already carried
through `fundamentals_deep` since B-49), or pair the absolute cut with a **margin floor** so
a thin-margin business must still earn something. Both are one-line additions to B-49's
`CRITERIA` table.

### P/E < 20

Fine as a **guard**, weak as a **signal** — already `max_pe` in B-49, defaulted to 25.
Nothing to build. Worth noting it excludes loss-makers entirely, which for a contra screen
is a real cost: the deepest turnarounds have no P/E at all. B-50 exists partly for that.

### Order book > market cap

**The strongest of the three, and the only one that is genuinely blocked.** For EPC,
capital goods, defence and infra, order book is forward revenue already contracted, so
book/mcap is a hard-to-argue-with cheapness measure — and meaningless for FMCG, banks or
services, so it needs a **sector gate before it is even computed**.

> [!important] Order book is not in any structured free feed.
> It lives in investor presentations and concall transcripts — **PDFs**. That is the same
> data shape as the buyback price (also PDF-only, verified: 0 of 28 buyback filings carried
> a price in their announcement text). One PDF fact-extractor unlocks both, which is why
> they are sequenced together below.

### On buybacks — your framing is the right one

You said a buyback is good news only when it is EPS-accretive with growth intact, and left
the rest to judgement. That splits cleanly into a computable part and a subjective part,
and the roadmap should encode only the first:

- **Objective:** buyback size ÷ shares outstanding → **EPS accretion %**; premium to CMP;
  route (tender vs open market); promoter participation; size as % of market cap.
- **Subjective, left to you:** whether the growth is intact and the accretion is worth it.

The supporting evidence is real and — importantly — **specific to contra**: Ikenberry,
Lakonishok & Vermaelen (1995, JFE) found +12.1% four-year abnormal return after open-market
repurchases overall, **+45.3% for value stocks, and no drift at all for glamour stocks**.
The signal lives exactly where B-49 and B-50 already look.

> [!warning] India's buyback tax changed on 1 Oct 2024.
> The whole consideration is now deemed dividend at slab rates (up to ~51% with surcharge
> and cess), with **no cost-of-acquisition deduction**. *Tendering for the premium* is
> largely destroyed for taxable residents; *holding because management committed cash above
> market* is intact. Every pre-2024 study ran under a different regime. Encode the signal,
> not the trade.

## Part 3 — what the list leaves out

Four contra methods with better support than several of the seven:

1. **Piotroski F-Score — the single biggest omission.** Nine binary accounting tests
   (profitability, leverage, efficiency). Piotroski (2000) found high-book-to-market names
   scoring 8–9 beat the market by **7.5% a year** while those scoring 0–1 lagged by
   **8.3%** — i.e. it works *specifically inside the value universe*, by discarding the
   losers. **This is the value-trap guard B-49 does not have**, and `grep -i piotroski
   tools/` returns nothing. Every input is already computed by `fundamentals_deep`.
2. **Insider / promoter buying.** Free NSE data already flowing through `ownership_cache`
   and `smallcap_discovery`; currently scored for *institutional* conviction only.
   Promoters buying into weakness is the cleanest available insider signal.
3. **Long-term reversal with a quality gate** (De Bondt–Thaler shape): 3–5 year losers,
   filtered by F-Score so it is not a bankruptcy screen. Distinct from
   [[concepts/Mean-Reversion]], which is a 2–5 day oscillator trade.
4. **Forced selling / index deletion.** Mechanical, dated, non-informational selling —
   the cleanest "price moved for a non-fundamental reason" event there is, and NSE
   publishes index reconstitution free.

## Part 4 — the roadmap

Ordered by (evidence strength × data availability) ÷ effort. Each phase is **gated on the
measurement of the previous one**, which is the discipline the seven-strategy list has none of.

### Phase 0 — pay the measurement debt first  *(blocks everything)*
**B-34, B-49 and B-50 all owe the same experiment**, and it should be built once, not
three times: enter on the signal, hold N days, matched non-signalling control, **exact
rotation p-value** (Welch is invalid here — overlapping forward windows already produced
one false 0.031 that read 0.32 under rotation). Deliverable: one reusable event-study
harness. Until it exists, every screen below ships as a reading list.

### Phase 1 — Piotroski F-Score  *(cheapest, highest-evidence)*
Nine tests over data `fundamentals_deep` already returns. Wire as a **column and a guard**
in B-49 and B-50, not a new screen. Immediately answers "is this cheap stock cheap for a
reason?" Also the natural gate for Phase 4.

### Phase 2 — make the sentiment gate actually gate  *(B-32, already filed)*
The best-supported strategy on the list, and the repo computes the inputs and then only
*describes* them — [[analyses/Noise-Regime-Coverage-Postmortem]] found output stays ~100
longs regardless of tape. Turning a description into a throttle is the largest behavioural
change available, and it costs no new data.

### Phase 3 — buyback + promoter-buying signals  *(B-52)*
`fetch_announcements` to stop discarding `attchmntFile`; parse the buyback PA for price,
size and route; compute premium, **EPS accretion**, size/mcap, and promoter participation
from `ownership_cache`. Ship as a screen with the tax caveat on its face.

### Phase 4 — PDF fact extractor → order book  *(B-53, unlocked by Phase 3)*
Generalise Phase 3's parser into a cached fact extractor over investor-presentation and
concall PDFs. First fact: **order book**, sector-gated to EPC / capital goods / defence /
infra, expressed as book ÷ market cap. Highest-value screen of the three you named and the
only one needing new machinery.

### Phase 5 — long-term reversal, F-Score gated  *(B-54)*
3–5 year losers ∩ F-Score ≥ 7 ∩ not distressed. Needs Phase 1. Cheap once it exists.

### Deprioritised, with reasons
- **Macro cycle reversal** — too few observations to test; discretionary by nature.
- **Astro-contra** — measured negative where measured. Do not build on it; finish testing
  what exists before extending it.
- **POC/exhaustion confluence** — measured negative, factors sign-inverted. The SVP overlay
  stays as a reading aid; it must not become a contra trigger.

> [!key-insight]
> The list's implicit model is *more layers → more conviction*. This repo's own results say
> the opposite: it has 43 indicators, hid 9 of 41 scanners for redundancy, and measured
> three of four new indicators to null. **The binding constraint is not more strategies —
> it is Phase 0.** One shared event-study harness converts every screen already built from
> a plausible story into a measured one, and that is worth more than all seven items on the
> list combined.
