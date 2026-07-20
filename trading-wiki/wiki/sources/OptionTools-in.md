---
title: "OptionTools.in — Nifty Trade Brief (recurring source)"
category: source
tags: [options, nifty, oi, pcr, max-pain, intraday, brief]
created: 2026-07-07
updated: 2026-07-07
sources: 1
related: [analyses/Nifty-Options-EOD-20260707]
---

# OptionTools.in — Nifty Trade Brief (recurring source)

## Metadata
- **URL:** https://www.optiontools.in/analysis/brief?date=YYYY-MM-DD
- **Format:** Web tool — daily one-page trade brief for NIFTY (also serves BankNifty/FinNifty per site; only NIFTY ingested here).
- **Access:** Google sign-in gated. Public preview shows only the login wall — full page must be pasted from a logged-in browser session or ingested via authenticated scraper.
- **Ingested by:** manual paste from user's browser session.
- **First ingest:** 2026-07-07.

## What This Source Provides
A structured, per-session summary computed off the NSE options chain, at a chosen intraday window (5 / 15 / 30 / 60 / 120 / 180 min or full day). Each brief carries:

- **Session snapshot:** spot, % from open, max pain, ATM CE/PE buildup type, heaviest CE/PE OI (with strike + moneyness), largest OI change since open, largest recent-window OI change, top volume strike.
- **Recent flow blocks (5/15/30 min):** spot delta, top CE/PE volume-change strikes, top CE/PE OI-change strikes, and a short narrative flag (put-side vs call-side dominant, unwinding vs buildup).
- **Price & session panel:** spot move from open, intraday trend path (Up/Down sequence), intraday range position (% of session range).
- **OI buildups panel:** ATM CE/PE labels (Short buildup / Long unwinding / Long buildup / Short covering), ITM CE/PE OI changes, key OTM CE/PE OI changes since open, "outer CE" aggregate.
- **Open interest panel:** Top-2 CE and PE by absolute OI, top-2 by OI-change-since-open, top-2 by OI-change-last-30-min.
- **Max pain + PCR line.**
- **Volume panel:** Top-2 ITM CE and ITM PE volume for both the selected window and the last 30 min (with same-strike opposite-side volume for context); top-2 CE/PE volume in the selected window; top-2 CE/PE volume rise in last 30 min.

## Interpretation Cheat-Sheet (from the labels the tool uses)
- **Short buildup (CE):** OI ↑ with price ↓ → new call sellers dominating → resistance being defended above.
- **Short covering (PE/CE):** OI ↓ with favorable price move for shorts closing → tail-risk relief on that side.
- **Long buildup:** OI ↑ with price ↑ (CE) or price ↓ (PE) → new directional longs entering.
- **Long unwinding:** OI ↓ with price move against the long side → existing longs booking / getting out.
- **Max pain** = strike at which total option-writer payout is minimised → magnet-level thesis for expiry pinning.
- **PCR** = put OI / call OI; > 1 typically read as bearish sentiment already priced (contrarian bullish tell at extremes), < 1 as bullish sentiment already priced.

## Actionable Insights
- **Ingest recurring:** file each day's brief as its own `analyses/Nifty-Options-EOD-YYYYMMDD.md`, back-link to this source page. Over time this produces a searchable regime tape (max-pain drift, ATM buildup patterns before big moves, PCR extremes).
- **Cross-link discipline:** every daily brief analysis should link the max-pain level, the ATM strike, and any large-OI strikes to the [[entities/NIFTY]] page (create when a Nifty entity page is warranted). Long-term this builds a level book.
- **Contradictions to flag over time:** if OptionTools' "Long unwinding" reading conflicts with a same-day price-action / VWAP read (e.g. [[concepts/VWAP]] showing steep slope + widening bands = continuation), record it — mismatches are where the interpretive edge is.

## Contradictions with Existing Wiki
- None yet. This is the first options-flow source ingested; establishes the terminology used going forward.

## Pages Updated
- Created: `wiki/analyses/Nifty-Options-EOD-20260707.md` (first brief)
- Updated: `wiki/index.md`, `wiki/log.md`
