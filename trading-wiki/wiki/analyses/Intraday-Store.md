---
title: "Intraday store — the piece three studies were blocked on, and what it can actually answer"
category: analysis
tags: [infrastructure, intraday, sqlite, data-quality, perishable-data, FA-2, rahu-kaal, volume-profile, backtest]
timeframe: intraday
created: 2026-08-09
updated: 2026-08-09
sources: 0
related:
  - concepts/Panchang.md
  - concepts/Volume-Profile.md
  - strategies/4H-Wick-Zone-FVG-Setup.md
  - analyses/Financial-Astrology-Sector-Week-Roadmap.md
  - analyses/Backtest-Harness.md
  - analyses/Market-Brief-Card.md
---

# Analysis: Intraday store — 2026-08-09

## Thesis

Three separate claims got recorded as untestable in three days, all for the same reason: **`chart_server` fetches intraday bars and nothing persisted them.** Built as [intraday_store.py](tools/intraday_store.py).

| Blocked study | Needs | Recorded in |
|---|---|---|
| **FA-2** — do NIFTY returns inside Rahu Kaal differ from outside? | intraday bars, per weekday | [[analyses/Financial-Astrology-Sector-Week-Roadmap]] |
| **80% value-area traverse rule** | 30m bars | [[concepts/Volume-Profile]] |
| **4H wick-zone setup** | 4H zone + 15m triggers | [[strategies/4H-Wick-Zone-FVG-Setup]] |

## Evidence For — the reason it had to be built *now*, not when needed

> [!key-insight] Intraday data is perishable. Daily data is not.
> Yahoo serves intraday history as a **rolling window**. Measured against RELIANCE.NS, 2026-08-09:
>
> | Interval | Deepest backfill | Bars | Usable for a ~90-min window study? |
> |---|---|---|---|
> | 1m | **~8 days** | 2,555 | no |
> | 5m | ~81 days | 4,340 | not yet |
> | 15m | ~81 days (~58 sessions) | 1,450 | not yet |
> | **1h** | **~1,075 days (~3 years)** | **5,053** | **yes, coarsely** |
>
> Asking for more than the ceiling returns an **empty frame with an error**, not a truncated one — over-asking loses everything, which is why `MAX_PERIOD` is a measured lookup table rather than an optimistic guess.
>
> **The consequence: every day the store does not run is a day of 15m data that can never be recovered.** Daily bars will still be there in five years; 15m bars from last quarter will not. That asymmetry — not any single study — is the argument for a schedule.

## What is stored now

Backfilled 2026-08-09: **6 symbols × 3 intervals = 65,056 bars, 11.7 MB.** `^NSEI` plus five large-caps, at 1h / 15m / 5m.

- `^NSEI` 1h: **5,057 bars, 724 sessions, 2023-08-28 → 2026-08-07 (1,075 days).**
- 15m and 5m: 58 sessions each — the 60-day ceiling, and the number that only grows by running.

Design points worth keeping in mind when reading from it:
- **Idempotent**: PK `(symbol, interval, ts)` + `INSERT OR REPLACE`. Re-running a backfill overwrites; a half-failed run is just re-runnable.
- **Timestamps carry an explicit +05:30 offset, never naive.** A naive intraday timestamp is the same class of bug as `ephem.localtime` silently using the machine's timezone ([[concepts/Panchang]]) — and here it would misplace every clock-window slice by 5h30 while looking fine.
- **Failures are logged, not swallowed**: `fetch_log` records every attempt with its reason, and an empty frame is recorded as an error rather than as a successful no-op. The frozen-feed lesson again — the dangerous failure is the fetch that quietly returns nothing new.
- **`session_slice()`** is the read the three studies need: hand it a window from `panchang.day_parts()` and it returns the bars inside it.
- The `.db` is **gitignored** (`*.db`, as with `reversal_calendar.db` and `trading_bramha.db`), so the code is versioned and the data is not. See the risk below.

## Evidence Against — what the store does NOT fix

> [!warning] Rahu Kaal barely overlaps NSE trading hours, and on Tuesday it essentially does not
> This surfaced immediately on joining the store to `panchang.day_parts()`: of 724 stored `^NSEI` sessions, only **592** contain even one 1h bar inside Rahu Kaal — and the per-weekday split is wildly uneven (Mon 142, **Tue 17**, Wed 144, Thu 145, Fri 143).
>
> The cause is structural, not a data gap. Rahu Kaal occupies a fixed 1/8 day-part per weekday, and the NSE session is 09:15–15:30. Sampling every weekday across 2025:
>
> | Weekday | RK part | Window range (seasonal drift) | Overlaps the session |
> |---|---|---|---|
> | Monday | 2nd | 07:39–10:02 | 52/52, but **starts before the 09:15 open** |
> | **Tuesday** | 7th | 15:11–17:41 | **14/52 — almost entirely after the 15:30 close** |
> | Wednesday | 5th | 12:21–14:23 | 53/53, **fully inside** |
> | Thursday | 6th | 13:47–16:01 | 52/52, **tail runs past the close** |
> | Friday | 4th | 10:55–12:52 | 52/52, **fully inside** |
>
> **So FA-2 is only cleanly askable on Wednesday and Friday.** Monday is truncated at the open, Thursday at the close, and **Tuesday is untestable on Indian equities** — its window is a post-market phenomenon.
>
> This is the kind of constraint that would otherwise have produced a confusing null result: pool all five weekdays and roughly a third of the "inside Rahu Kaal" mass is either pre-open, post-close, or absent, diluting any effect toward zero for a purely mechanical reason. **Design the test per weekday, and lead with Wednesday and Friday.**

Other limits:
- **The 80% value-area rule still cannot be tested properly.** It is specified on two consecutive 30-minute bars, and 30m/15m depth is 58 sessions. Testable in a year of accumulation, not today. 1h is too coarse for a rule whose entry condition is a 30-minute hold.
- **The 4H setup remains untestable** for the same reason — its trigger leg is 15m.
- **Six symbols is a thin universe.** Fine for FA-2 (an index question), inadequate for anything cross-sectional.
- **No backup for the perishable half.** Because `*.db` is gitignored, accumulated 15m/5m history exists only in this working copy. It happens to sit inside a **OneDrive-synced path**, which is real but incidental protection — nobody chose it as a backup strategy. Losing the file loses the accumulated fine-grained history permanently, while 1h could simply be re-fetched.

## Conclusion

**FA-2 is now testable at hourly resolution on Wednesday and Friday**, with ~144 sessions each — a real sample, and the first time any astro claim in this repo could be measured rather than asserted. The other two studies are unblocked *in principle* and gated on accumulation.

The store also converted a vague blocker into a precise one. "We need intraday data" was true but unactionable; "we need 15m depth beyond 58 sessions, and Rahu Kaal only overlaps the session on Wed/Fri" is something a study can be designed around.

## Action Taken / Plan

- ✅ `intraday_store.py` — backfill / update / coverage / `session_slice`, 21/21 behavioural checks, 65,056 bars stored.
- ✅ Measured Yahoo's per-interval ceilings and recorded them as a lookup rather than a guess.
- ✅ Surfaced the Rahu-Kaal-vs-session-hours constraint before any study was designed on top of it.
- ⏭ **Schedule `update` to run daily** — this is what makes 15m/5m accumulate. Not created here: standing configuration is the user's call. Without it the store's perishable half stops growing and the 80% rule and 4H setup stay blocked forever.
- ⏭ **FA-2 proper**: Wednesday/Friday, 1h bars inside vs outside Rahu Kaal, against a matched-window baseline with a significance test — the same shape as the [FVG fill study](tools/fvg_fill_study.py), which is the template for "test the claim against a control rather than against nothing".
- ⏭ Widen the universe if any cross-sectional intraday question appears.

## Outcome (fill in later)

## Related Pages

- [[concepts/Panchang]] — supplies the windows; the weekday-overlap table above is a fact about it
- [[analyses/Financial-Astrology-Sector-Week-Roadmap]] — FA-2, now unblocked for two weekdays
- [[concepts/Volume-Profile]] — the 80% rule, still gated on 30m accumulation
- [[strategies/4H-Wick-Zone-FVG-Setup]] — still gated on 15m accumulation
- [[analyses/Backtest-Harness]] — where FA-2 lands
