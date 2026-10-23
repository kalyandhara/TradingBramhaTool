---
title: "GitHub list — Design Resources for Developers (bradtraversy)"
category: source
tags: [design, ui, colors, fonts, icons, accessibility, charts, reference]
created: 2026-10-13
updated: 2026-10-13
sources: 1
related:
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Open-Backlog.md
  - analyses/Design-Review-2026-10-13-Look-And-Feel.md
---

# GitHub list — Design Resources for Developers

## Metadata
- Author: Brad Traversy and contributors. MIT licence. https://github.com/bradtraversy/design-resources-for-developers
- Format: a single `readme.md` of links (no code, no package, **not installable as an MCP server** — checked 2026-10-13 when the owner asked to add it as one).
- Ingest trigger: owner wants to improve the tool's look and feel. Ingested as a REFERENCE shortlist; the full list has hundreds of entries across ~35 sections, most irrelevant to a Streamlit + HTML-chart desk (stock photos, mockups, React/Vue/Angular kits, Chrome extensions).

## Key Takeaways
- It is a directory, not guidance: it says where to find palettes, fonts and icons, not which to use. Choices still need a rule (below).
- **Accessibility is the most useful slice for this desk**, because the tool encodes meaning in colour (green/red candles, BUY/SELL, verdict chips) and red/green is the commonest colour-blind confusion.
- **The list has no dashboard or dark-mode section.** For those, the design systems it links (IBM Carbon, GitHub Primer, Microsoft Fluent, the ETrade design system) are the relevant references — Carbon in particular publishes data-visualisation and dark-theme guidance.
- **Our price-chart library is not on it.** The Chart Tool uses TradingView Lightweight Charts; the listed chart libraries (ECharts, ApexCharts, Chart.js, D3) only matter for non-price charts.

## Detailed Notes — the shortlist that fits this desk

**Colour and contrast (use these before changing any colour)**
| Resource | Why it matters here |
|---|---|
| Color Brewer 2 — colorbrewer2.org | Colour-blind-safe sequential/diverging palettes: heatmaps, breadth, sector rotation |
| whocanuse — whocanuse.com | Shows who can read a given foreground/background pair (low vision, colour blindness) |
| Huetone — github.com/ardov/huetone | Builds accessible colour systems with lightness steps — for `rs.TOKENS` in both themes |
| InclusiveColors — inclusivecolors.com | Accessible palette scales with editable curves |
| Colorable — colorable.jxnblk.com | Quick contrast tester for a palette |
| A11ygator — a11ygator.chialab.io | WCAG scan of a whole page |

**Fonts**
| Resource | Why it matters here |
|---|---|
| Fontsource — fontsource.org / Google Webfonts Helper | SELF-HOST fonts. The PWA works offline and `sw.js` caches assets, so a CDN font would break offline and a cached font needs a versioned file name (the PWA cache trap) |
| Google Fonts / Bunny Fonts | Source of open fonts; Bunny is the privacy-preserving mirror |
| Dev Fonts — devfonts.gafi.dev | Monospace candidates for prices and tables (tabular figures keep columns aligned) |
| Fontshare (Indian Type Foundry) | Open fonts with Devanagari coverage, relevant to the Vedic/Panchang pages |
| Lexend — lexend.com | Variable font designed for reading ease; a candidate for beginner-mode text |

**Icons** — pick ONE family and stay with it
| Resource | Why it matters here |
|---|---|
| Tabler Icons / Lucide / Phosphor | Open-source, consistent stroke sets with finance and chart glyphs; good for the B-150 indicator browser and the page rail |
| Iconify / Icones | Search across sets (the Supericons tools in this environment already cover search) |
| Cryptoicons / Simple Icons | Crypto tickers and brand marks |

**Design systems and principles (for patterns, not to copy wholesale)**
| Resource | Why it matters here |
|---|---|
| IBM Carbon — carbondesignsystem.com | Data-viz colour, dark theme, dense data tables |
| GitHub Primer, Microsoft Fluent | Mature dark themes and dense, tool-style layouts |
| ETrade Design System — etrade.design | A finance product's design system |
| Laws of UX — lawsofux.com; Checklist Design — checklist.design | Short principles and per-component checklists for reviews |
| Webframe, Design Vault | Screens from real web apps, for layout ideas |

## Actionable Insights
1. **Run a contrast and colour-blindness pass before any restyle** (whocanuse / Color Brewer). The desk's meaning-carrying colours are the risk, not the decoration.
2. **One icon family, self-hosted**, with hashed file names (sw.js).
3. **Monospace or tabular figures for every number column.**
4. Restyling follows a written token change in `rs.TOKENS` (Streamlit) and the `:root` variables in `chart_dashboard.html`, so the two surfaces stay one system.

## Contradictions with Existing Wiki
None. It adds a reference library; [[analyses/Dashboard-UI-Roadmap]] remains the plan.

## Pages Updated
- [[analyses/Design-Review-2026-10-13-Look-And-Feel]] — the look-and-feel critique that uses this shortlist.
