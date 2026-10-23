---
title: "Design Review — 2026-10-13: look and feel of Home and the Chart Tool"
category: analysis
tags: [design-review, ui, accessibility, color, typography, chart-tool, home]
timeframe: milestone-plan
created: 2026-10-13
updated: 2026-10-13
sources: 1
related:
  - sources/Design-Resources-For-Developers.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Open-Backlog.md
---

# Analysis: Design Review — 2026-10-13, look and feel

## Thesis
The desk's look is held back less by taste than by three measurable things: the
colour that means "up" is too faint to read, the two surfaces (Home, Chart Tool)
look like two different products, and the page order on Home buries the one
decision it exists to give. Reviewed live (fresh Streamlit process on :8501,
chart server on :5001), contrast computed with the WCAG formula, against the
shortlist in [[sources/Design-Resources-For-Developers]].

## Evidence For — findings

### Colour and contrast (measured, WCAG AA needs 4.5:1 for normal text)
| Token (report_style.TOKENS) | On `surface` #fffdf8 | Verdict | Replacement | New ratio |
|---|---|---|---|---|
| `good` #16a34a | **3.24** (2.93 on `good_soft`) | FAIL — every gain, "Advancing", "Bull" label | #15803d (green-700) | 4.93 |
| `accent` #d97706 | **3.13** | FAIL — the small orange section headings | #b45309 (amber-700) | 4.94 |
| `absent` #9ca3af | **2.50** | FAIL if used for text | text only at ≥ 18px, or #6b7280 | — |
| `risk` #dc2626 | 4.75 (4.29 on `good_soft`) | borderline | #b91c1c (red-700) | 6.36 |
| `info` #2563eb / `text_muted` #7a6858 | 5.08 / 5.23 | pass | — | — |
| Chart Tool up #26a69a / down #ef5350 on #131722 | 5.97 / 5.13 | pass | — | — |

- `#16a34a` is also **hard-coded 26 times** in `dashboard_app.py`, so a token change alone will not reach every gain colour.
- **Colour-blind safety is half done.** Index cards and KPI tiles carry ▲/▼ arrows, so direction survives without colour. The breadth bars (Advancing/Declining, Above/Below, Bull/Bear) and the coloured card BORDERS rely on red vs green alone; red/green is the commonest colour-vision deficiency.

### Typography
- **Three text families on one page**: Streamlit's Source Sans, Segoe UI Variable (custom cards) and ui-monospace (numbers). Monospace for numbers is right (columns align); the two sans faces are not a choice, they are an accident.
- **Much of the explanatory text is 10–11px** (31 elements at 10px, 13 at 11px). Readable on a large monitor, a strain on a laptop, and below the 12px floor most design systems set for body copy.
- **Number formatting is inconsistent between tables**: the PPV table prints `5.30%`, the CPR × Volume Profile table on the same page prints `3.100000` and `4.470000` (raw floats).

### Hierarchy (Home)
- **First thing the eye lands on**: the row of index cards and sparklines. **The decision — TODAY'S VERDICT "STAND DOWN", position size 0%** — sits below them, at roughly two-thirds of the first screen. For a desk whose daily question is "can I take risk today?", the answer should be the first block.
- **A landing-page hero sits mid-page** ("Screening, research and risk — in one place", three CTA buttons, scanner counts) BELOW the verdict. A hero is for a first visit; on a daily-use page it pushes the shortlist down by a full screen.
- **Method notes run as grey paragraphs between sections** (e.g. the paragraph under the index cards, the one under the breadth row). They are the desk's honesty and should stay, but as collapsed "How this is measured" notes, not as walls of 10px text between data blocks.
- Every card has a border, and index cards add a red/green border — many competing outlines on one screen.

### Consistency between surfaces
| Element | Home (Streamlit) | Chart Tool | Effect |
|---|---|---|---|
| Theme | Warm cream / brown / amber, light | GitHub-dark blue-grey #131722, accent #58a6ff | Two products, not one desk |
| Body font | Source Sans + Segoe UI | system sans (-apple-system/Segoe UI) | Different rhythm |
| Up / down | #16a34a / #dc2626 | #26a69a / #ef5350 | Different greens and reds for the same meaning |
| Controls | Streamlit defaults | 10px text, buttons 17–18px tall (INDICATORS, range 1M/3M…), draw tools 24×22 | Chart controls are below the 24px minimum target size |

### Usability
| Finding | Severity | Recommendation |
|---|---|---|
| Gain colour fails contrast everywhere | 🔴 | Change `good` to #15803d and replace the 26 hard-coded uses with the token |
| Verdict below the market tiles | 🔴 | Move TODAY'S VERDICT to the top of Home, tiles after it |
| Chart Tool buttons 17–18px tall, 10px labels | 🟡 | 24px minimum height, 11–12px labels |
| Raw floats (`3.100000`) in a table | 🟡 | Format through one `fmt_pct` helper, 2 decimals |
| Hero block mid-page | 🟡 | Show it only to a first-time / beginner-mode user, or move to the bottom |
| Red/green-only breadth bars and card borders | 🟡 | Add a pattern or text label inside the bar ends; drop coloured borders in favour of the arrow + number |
| 10px explanatory text | 🟢 | 12px minimum; collapse method notes into expanders |

## Evidence Against — what works
- **Numbers in monospace** with ▲/▼ arrows and both absolute and % change — scannable and colour-blind-safe on the cards.
- **Honest absent states**: "DATA N/A — no name had a year of closes" is shown rather than a zero. Keep this pattern everywhere.
- **The verdict block itself is well built**: one large word, a size, a playbook line, and three columns (Caution / Favourable / Not checked) — the "not checked" column is unusual and valuable.
- **The Chart Tool's dark palette passes contrast** (secondary text 5.82, candles 5.1–6.0) and is a familiar trading-terminal look.
- A real token system already exists (`report_style.TOKENS`, tone → foreground/tint), so most fixes are one-line token changes plus removing hard-coded colours.

## Conclusion
Fix in this order, smallest change first: **(1) contrast tokens**, **(2) verdict to the top of Home**, **(3) one design language across both surfaces** (shared up/down colours and font first; full theme later). Filed as B-161…B-164.

## Action Taken / Plan
- Backlog B-161 (contrast tokens + hard-coded colours), B-162 (Home order: verdict first, hero conditional, method notes collapsed), B-163 (Chart Tool control sizes), B-164 (shared tokens across Home and Chart Tool; number formatting helper). None built.

## Outcome (fill in later)
- **2026-10-13 — B-161 done.** Tokens moved to the 800 level (the 700 level proposed above reached only 4.40–4.46 on `surface_alt` and the tints): good #166534, risk #b91c1c, accent #a14a0b, absent #636a75. 70 hard-coded copies replaced. Live: 7 of 1,024 text elements still under 4.5, all brand orange or hidden. Brand orange #ea580c (3.5:1) left to the owner.
- **2026-10-13 — B-162 done.** Verdict first; index and breadth strips after it; hero moved to the foot of Home; method notes collapsed into expanders; breadth bars gain ▲/▼ and a segment gap.
- **2026-10-14 — B-163 done.** Chart Tool header, range and draw controls at 24px / 11–12px labels; 8-chart header held at two rows by tightening horizontal spacing in narrow panes. Sub-plot 16px buttons not changed.
- **2026-10-14 — B-164 done.** One number formatter for styled tables (root cause: pandas Styler's 6-decimal default); Chart Tool on the same sans/mono stacks as Home. The "config font not applied" finding was a stale process. Up/down: owner kept both palettes (cream-tuned green/red on Home, TradingView teal/red on the chart); the chart's 83 copies are now one named pair.

## Related Pages
- [[sources/Design-Resources-For-Developers]] — the reference shortlist (contrast checkers, fonts, icons, design systems)
- [[analyses/Dashboard-UI-Roadmap]]
- [[analyses/Open-Backlog]]
