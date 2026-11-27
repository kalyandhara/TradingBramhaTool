# Multi-Chart dual pick replay (short design)

**Date:** 2026-11-26 · **Approved:** owner ("lets go", after the design was laid out in chat) ·
**Builds on:** `2026-11-26-pick-replay-design.md` · **Size:** small change

## Intent
Open any audited pick in the in-house Multi-Chart (chart_server, :5001) as two
side-by-side panes: the chart as it stood on the pick day, and everything since —
the owner's "Dual Replay" sketch, using the full chart tool rather than a static figure.

## Design (as built)
- **Link:** Pick replay gets "Open in Multi-Chart ↗". `rec_audit_replay.multichart_url`
  builds `?symbol&exchange=NSE&tf=1d&layout=replay&replay=<pick date>&entry&stop&target
  &sdate&skind=S|T&sector&rank&label`. `layout=replay` keeps the standalone tool's saved
  layout untouched. Far-off (stale) levels are left out, as on the replay page.
- **Pane 1 — BEFORE PICK:** bars cut at the pick day in the browser right after the
  fetch (`RPM.cutBars`), so every indicator is computed without hindsight; live ticks
  and the tick poll skip this pane. EMA 20, dashed entry / stop / target, 60-bar view,
  banner with pick date, rank and families.
- **Pane 2 — AFTER PICK:** full history; EMA 20 and Event Markers on (E = results,
  N = filings); markers PICK (entry session), S / T (audit's first stop / target hit),
  V (volume breakdown); NIFTY 500 (`^CRSLDX`) and the sector index drawn from the
  entry-day open, like the audit's excess.
- **V is a desk rule, not a measured signal:** first close below the prior 20-session
  low on ≥ 1.5× the prior 20-session average volume. Labelled as such in the banner.
- **D (downgrade)** waits for daily score tracking (Project 4).

## Non-goals
No change to the standalone Multi-Chart; no new server route; no fetch on the audit page.

## Files
`tools/replay_mode.js` (pure, node-tested in `test_replay_mode.py`), `chart_dashboard.html`
(script tag, `REPLAY`, deep-link branch, cut in `loadData`, `applyReplay`), `sw.js`
(shell + CACHE_VERSION v3), `rec_audit_replay.multichart_url`, `rec_audit_page`.
