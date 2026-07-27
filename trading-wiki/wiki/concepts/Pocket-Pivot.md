---
title: "Pocket Pivot (Morales/Kacher)"
category: concept
tags: [pocket-pivot, volume, accumulation, morales, kacher, minervini-adjacent, entry]
created: 2026-07-23
updated: 2026-07-23
sources: 1
related: [concepts/PEAD, concepts/VCP, concepts/Volume-Profile, concepts/Distribution-Days]
---

# Pocket Pivot (Morales/Kacher)

## Definition
A **pocket pivot** is an early accumulation entry signal from Gil Morales & Chris
Kacher (*Trade Like an O'Neil Disciple*). The core condition: an **up day whose
volume exceeds the highest DOWN-day volume of the prior N sessions** — evidence
that buying demand has just overwhelmed the largest recent supply, often *before*
a conventional base breakout. It's a volume-signature entry inside a constructive
base, not a breakout of resistance.

## How to Use
Enter as institutional demand reappears within an orderly base — earlier and with
tighter risk than waiting for the pivot breakout. In a PEAD context
([[concepts/PEAD]]), counting pocket pivots *since the earnings day* gauges
ongoing accumulation through the drift window.

## Variants / Parameters
Canonical construction (per [[sources/TV-PEAD-Screener-PineScript]]):
- **Volume trigger:** `up day AND green candle AND volume > highest down-day volume in last N bars` (N ≈ 10). Fallback hurdle when there are no down days in the window (strong trend / [[concepts/High-Tight-Flag]]): volume > 50-day average.
- **MA proximity:** the low should sit near the 10-day or 50-day MA (typ. within 2–3%). Handles gap-and-go via prior-close-near-MA and body-crosses-MA variants.
- **Not extended:** reject if more than ~10% above the 10-day MA (climax-run avoidance).
- **Trend filters:** require above the 50-day MA (canonical); optionally above the 200-day MA.

## Common Mistakes
- **Volume-only detection.** Dropping the MA-proximity/extension filters flags
  extended stocks and falling knives — the volume trigger alone is not enough.
- **Buying below the 50-day MA** without a constructive pattern (Morales/Kacher warn against it).
- **Counting climax pivots.** An over-extended pivot far above the 10-MA is late, not early.

## Related Concepts
- [[concepts/PEAD]] · [[concepts/VCP]] · [[concepts/Distribution-Days]] · [[concepts/Volume-Profile]]

## Examples in This Wiki
- Used as PEAD criterion #5 (count since earnings) in [[sources/TV-PEAD-Screener-PineScript]];
  candidate Phase-3 detector in [[analyses/PEAD-Scanner-Roadmap]].

## Sources
- [[sources/TV-PEAD-Screener-PineScript]] — pocket-pivot port with full filter set.
