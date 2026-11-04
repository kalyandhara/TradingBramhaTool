---
title: "Filing PDF Data Probe — the text is there, a regex is not enough"
category: analysis
tags: [filings, nse, corporate-announcements, data-probe, b-112, measured-fail]
timeframe: swing
created: 2026-10-30
updated: 2026-10-30
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/CVD-Data-Probe.md
---

# Analysis: Filing PDF Data Probe — B-112 — 2026-10-30

## Thesis

B-112 asked whether the deal amounts that live only in filing PDFs ("₹126 Cr
contract" filed as "General Updates — Reg. 30") can be recovered, and said:
**probe the data first, build the extractor only if the probe says the text is
there.** Three questions, in the order that can kill it: (1) are the
attachments text PDFs or scans, (2) how often does the existing amount regex
find a figure in the extracted text, (3) when it does, is it the deal amount?

Bars committed in `tools/filing_pdf_probe.py` before the first run (sha256
`85f258da…bb63cb` at 11:59 ET): text layer ≥ 80% of fetched PDFs; recovery
≥ 50% of text PDFs in the deal buckets; **precision ≥ 80% of a 20-item random
sample, judged by hand**. Build only if all three pass.

Sample: 3,957 filings over 5 days (IST, to 2026-10-30), two groups of 60 PDFs
drawn with seed 112: **deal** (ORDER_WIN / M&A / FUND_RAISE / CAPACITY whose
API text had no amount, 177 eligible) and **generic** (filed as "General
Updates" / "Updates", 518 eligible).

## Evidence

| | v1 (as committed) | v2 (same 120 PDFs, regex fixed) | Bar |
|---|---|---|---|
| Fetched | 120 / 120 | 120 / 120 | — |
| **Text layer** | **100%** | **100%** | ≥ 80% ✅ |
| Recovery, deal group | 95% (57/60) | 82% (49/60) | ≥ 50% ✅ |
| Recovery, generic group | 85% (51/60) | 37% (22/60) | — |
| **Precision (hand, n=20)** | **10% (2/20)** | **50% (10/20)** | ≥ 80% ❌ |
| PDF size | median 581 KB, max 31.9 MB | same | — |

**v1 FAILED, and its recovery number was false.** 17 of its 20 "amounts" were
`₹,`: the regex accepted `rs` inside a word ("Towe**rs,**", "orde**rs,**")
followed by a bare comma. The bug was live in `nse_filings_feed.amount_from`,
which `filings_watch` and the Filings page use: 3 of 22 amounts on a week of
live filings read `₹,`, and because the bad match came first it HID real
figures ("orders, worth Rs 50 crore" → `₹,`). **Fixed the same day**:
`rs`/`inr` must start a word, the figure must contain a digit, "Crs" reads as
crore, and a per-unit price ("Rs.115 each", "per option") yields to any total
in the same text and is otherwise returned labelled (`₹115 each`).

**v2 is a second run, not a replacement.** It re-scores the exact PDFs of v1
(`--urls-from`), against the same bars, so the regex fix is judged on the
same documents. The v1 FAIL stands as recorded.

v2's hand judgement: ✓ CANBK ₹1,500 Cr (AT1 call), TONBO EUR 13M (order),
EXIDEIND ₹149.99 Cr (investment), COALINDIA ₹7,966 Cr (capex), SUBROS ₹150 Cr,
SRM ₹138.37 Cr (contract), FORTIS ₹277 Cr (acquisition), SAMBHV ₹1,480M,
APARINDS USD 100M, SCHNEIDER ₹211 Cr. ✗ QUESS total assets, MANAKCOAT share
capital, MANKIND share of profit, LCCPROJECT revenue (the order book was the
second figure), LEAPIND the target's revenue, three per-share prices worded
past the per-unit check (EMBDL "INR 111.51 (including…) per equity share",
ADVENZYMES "₹ 500/- (Rupees…) per Equity Share", KROSS issue price),
PHOENIXLTD `₹10` noise, OSWALGREEN AED 38M (not verifiable from context:
counted against).

## Conclusion

**The DATA question is answered YES and the EXTRACTOR question NO.**

- **The text is there.** 120 of 120 attachments carry a text layer; no OCR is
  needed. That was the part that could have killed B-112 outright, and it
  does not.
- **A first-figure regex is not an extractor.** Even fixed, half of what it
  returns is some other number in the filing: assets, revenue, share capital,
  a per-share price. A filing states many figures and the regex has no idea
  which one is the deal.
- **Per the committed rule, nothing is built.** A useful extractor would have
  to anchor on the phrase that names the figure ("value of the order",
  "contract for a value of", "consideration", "investment of", "aggregating")
  and would need its own pre-registered precision test, on a fresh sample, at
  the same 80% bar.

## Action Taken / Plan

- `amount_from` regex bug fixed in live code, with 4 new tests (36 in the file).
- Filings emails and the Filings page keep showing amounts only when the API
  one-liner states one; the PDF is still the link.
- B-112 row updated: probe done, extractor not built. The anchored extractor
  is a NEW item, not a continuation, because it is a different method.

## Outcome

Probe closed 2026-10-30. Whether an anchored extractor reaches 80% is open.

## Related Pages

- [[analyses/Open-Backlog]] (B-112)
- [[analyses/CVD-Data-Probe]] (the same probe-before-build pattern, B-48)
