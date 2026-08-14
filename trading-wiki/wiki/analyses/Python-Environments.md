---
title: "Two Python interpreters, different packages — the verification hazard"
category: analysis
tags: [infrastructure, environment, dependencies, ephem, streamlit, verification, gotcha]
timeframe: n/a
created: 2026-08-09
updated: 2026-08-09
sources: 0
related:
  - concepts/Panchang.md
  - analyses/Market-Brief-Card.md
  - analyses/Intraday-Store.md
---

# Analysis: Two Python interpreters, different packages — 2026-08-09

## Thesis

**This machine has two Python 3.14.4 installs with different packages, and the one that runs the app is not the one that is convenient to test with.** A feature was shipped verified against the wrong interpreter and failed on first use.

| | `pythoncore-3.14-64` | `Programs\Python\Python314` |
|---|---|---|
| **Runs the app** (`start.bat`, `.claude/launch.json`) | ✅ **yes** | no |
| streamlit | ✅ 1.57.0 | ❌ broken (starlette `DEFAULT_EXCLUDED_CONTENT_TYPES` ImportError) |
| pandas | ✅ 3.0.2 | ✅ 3.0.2 |
| yfinance | 1.2.1 | **1.4.1** |
| ephem | ❌ **was missing** → installed 2026-08-09 | ✅ 4.2.1 |

There is also a third on `PATH` — `hermes-agent\venv` — which has neither pandas nor numpy and is what a bare `python` resolves to. So `python foo.py` runs in an environment that can import almost nothing in this repo.

## What went wrong

`panchang.py` and the Morning Market Brief were verified with `Programs\Python\Python314`, chosen because it was the interpreter that had pandas. The dashboard runs `pythoncore-3.14-64`, which had no `ephem`. First real use produced:

```
Brief build failed: ModuleNotFoundError: No module named 'ephem'
```

**Two distinct defects, and only one was the missing package.**

1. **Undeclared dependency.** `ephem` was pip-installed ad-hoc into one interpreter on 2026-08-07 and the backlog item (B-14) was closed — but it was never added to `tools/requirements_pipeline.txt`. So "installed" was true of a machine state, not of the project. Any fresh environment would have failed the same way. Now declared.
2. **An optional dependency could erase the whole card.** `build_brief` imported `panchang` at function top, so a missing `ephem` took down the global quotes and sector breadth too — neither of which touches astronomy. The astro layer is now wrapped: the market half renders, and the astro block shows a warning naming the fix. `astro_trading.py` already modelled this correctly with its `HAS_EPHEM` flag; `panchang.py`'s consumer did not follow it.

## Evidence Against — why this is easy to repeat

- **`streamlit` only works in one of them and `ephem` only worked in the other**, so no single interpreter could run both the app and the astro verification until now. That is exactly the configuration that invites verifying in the wrong place.
- **`yfinance` versions differ (1.2.1 vs 1.4.1).** Nothing has broken on this yet, but any behaviour that depends on yfinance's frame shape — MultiIndex columns, tz handling, the `period` ceilings measured in [[analyses/Intraday-Store]] — could differ between what is tested and what runs.
- The failure mode is **silent until first real use**: import-time errors in an optional branch do not show up in a syntax check or in tests run under the other interpreter.

## Conclusion — the working rule

**Verify anything dashboard-facing with the interpreter from `.claude/launch.json`:**

```
C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Pure modules can be checked anywhere, but anything the app imports must be checked there. And **a new third-party import means adding it to `tools/requirements_pipeline.txt` in the same change** — an ad-hoc `pip install` records machine state, not project state, which is the mistake B-14 made.

## Action Taken / Plan

- ✅ `ephem` installed into `pythoncore-3.14-64` and **declared in `tools/requirements_pipeline.txt`** with a comment recording why.
- ✅ `build_brief` degrades: the astro layer is optional and cannot take down quotes or breadth. 11/11 checks including a simulated missing `ephem`.
- ✅ Side finding fixed while testing the degradation: `overall_tone()` returned `UNKNOWN` whenever breadth was absent — including when the user simply unticked the breadth checkbox — despite holding a usable Nifty change. It now degrades to a price-only read, with the caveat that price-only `STRONG` is the more generous call because breadth cannot veto it.
- ⏭ Reconcile the two environments, or retire one. Two 3.14.4 installs where each has something the other lacks is the actual root cause and it will keep generating this class of bug.
- ⏭ Consider pinning `yfinance` — the version skew is currently harmless and would not stay that way.

## Outcome (fill in later)

## Related Pages

- [[concepts/Panchang]] — the module whose dependency this was
- [[analyses/Market-Brief-Card]] — the feature that failed
- [[analyses/Intraday-Store]] — measured yfinance behaviour that could differ across the version skew
