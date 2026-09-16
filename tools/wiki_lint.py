#!/usr/bin/env python3
"""wiki_lint.py — health check for the trading wiki, per its CLAUDE.md LINT spec.

Checks, in order: index-header accuracy · dead links · orphans · frontmatter
gaps · staleness · schema sections · `sources: N` vs listed sources · pages
missing from the index · phrases that go false when code ships.

Run: `python tools/wiki_lint.py`

Two things this deliberately does NOT do, both learned the hard way on
2026-08-09:

* **It reports `sources: N` mismatches, it does not fix them.** The counter
  over-counts pages whose source entries carry indented sub-references
  (Kelly-Criterion reads 4 where the page has 2). A wrong count written
  confidently is worse than a known-inconsistent one.
* **It ignores wikilinks inside inline code.** The first version flagged the
  bare-name *examples* in the lint's own log entry as dead links — prose about
  links is not a link. Anything inside backticks is stripped before matching.
"""
from __future__ import annotations
import io, re, sys, collections, datetime as dt, pathlib

# Windows consoles default to cp1252 and this lint QUOTES the very prose it
# scans -- em dashes, arrows, circled digits. It died mid-report on a circled
# digit in a roadmap title (B-82), which is the same defect `claims_lint`
# records against itself: a tool that reports on prose must be able to print
# prose.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Derived, not typed. The absolute path worked on exactly one machine, and a
# lint nobody else can run is a lint that only ever gets run here.
ROOT = pathlib.Path(__file__).resolve().parent.parent / "trading-wiki" / "wiki"

#: The stale-page check measures against this.
#:
#: It was HARDCODED to `dt.date(2026, 8, 9)` and stayed there for 38 days (B-82).
#: So section 5 was not reporting "pages 30+ days old" -- it reported pages 30+
#: days old *as of a date in the past*, drifting further from the truth every day
#: it was not edited, while every page updated after 2026-08-09 read as a
#: NEGATIVE age. **The lint that exists to find claims which go false with time
#: contained one**, in the single line where time enters it.
TODAY = dt.date.today()
SPECIAL = {"index", "log", "overview"}

REQUIRED_FM = ("title", "category", "tags", "created", "updated", "sources", "related")
SECTIONS = {
    "concept":  ["Definition", "How to Use", "Variants / Parameters",
                 "Common Mistakes", "Related Concepts", "Examples in This Wiki", "Sources"],
    "strategy": ["Core Idea", "Setup Criteria", "Entry Rules", "Exit Rules",
                 "Timeframe", "Best Market Conditions", "Worst Market Conditions",
                 "Backtest / Track Record", "Examples", "Related Concepts", "Sources"],
    "source":   ["Metadata", "Key Takeaways", "Detailed Notes", "Actionable Insights",
                 "Contradictions with Existing Wiki", "Pages Updated"],
    "analysis": ["Thesis", "Conclusion", "Related Pages"],
    "entity":   ["Profile", "Sources"],
}

pages: dict[str, dict] = {}
for p in sorted(ROOT.rglob("*.md")):
    key = p.relative_to(ROOT).with_suffix("").as_posix()
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    fm = {}
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end > 0:
            for line in txt[3:end].splitlines():
                m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
                if m:
                    fm[m.group(1)] = m.group(2).strip()
    # Prose ABOUT links is not a link: drop fenced blocks and inline code
    # before extracting wikilinks, or a lint entry that quotes a bad link
    # gets reported as containing one.
    linkable = re.sub(r"```.*?```", "", txt, flags=re.S)
    linkable = re.sub(r"`[^`\n]*`", "", linkable)
    pages[key] = {"path": p, "text": txt, "fm": fm,
                  "headings": re.findall(r"^#{2,4}\s+(.+)$", txt, re.M),
                  "links": set(re.findall(r"\[\[([^\]|#]+)", linkable)),
                  "mdlinks": set(re.findall(r"\]\((?!http)([^)]+\.md)\)", txt))}

content = {k: v for k, v in pages.items() if k not in SPECIAL}
print(f"WIKI LINT — {TODAY}")
print(f"  {len(pages)} .md files ({len(content)} content pages + {len(SPECIAL)} special)")
by_cat = collections.Counter(v["fm"].get("category", "?") for v in content.values())
print(f"  by category: {dict(by_cat)}")

def head(t): print(f"\n{'='*74}\n{t}\n{'='*74}")

# ── 1. index header counts ──────────────────────────────────────────────────
head("1. INDEX HEADER vs REALITY")
idx = pages["index"]["fm"]
claimed_pages = int(idx.get("pages", 0) or 0)
src_pages = sum(1 for k in content if k.startswith("sources/"))
claimed_src = int(idx.get("sources_ingested", 0) or 0)
print(f"  index says pages: {claimed_pages}   actual .md files: {len(pages)}  "
      f"content pages: {len(content)}   {'OK' if claimed_pages in (len(pages), len(content)) else '<-- MISMATCH'}")
print(f"  index says sources_ingested: {claimed_src}   actual sources/ pages: {src_pages}  "
      f"{'OK' if claimed_src == src_pages else '<-- MISMATCH'}")
print(f"  index updated: {idx.get('updated')}")

# ── 2. dead wikilinks ───────────────────────────────────────────────────────
head("2. DEAD LINKS")
dead = collections.defaultdict(list)
for k, v in pages.items():
    for l in v["links"]:
        t = l.strip()
        if t not in pages and t.lstrip("./") not in pages:
            dead[k].append(f"[[{t}]]")
    for ml in v["mdlinks"]:
        cand = (v["path"].parent / ml).resolve()
        if not cand.exists() and "tools/" not in ml and not ml.startswith("http"):
            dead[k].append(f"({ml})")
if dead:
    for k, ls in sorted(dead.items()):
        print(f"  {k}: {', '.join(sorted(set(ls))[:6])}")
    print(f"  TOTAL: {sum(len(v) for v in dead.values())} dead refs in {len(dead)} pages")
else:
    print("  none")

# ── 3. orphans ──────────────────────────────────────────────────────────────
head("3. ORPHAN PAGES (no inbound wikilink from any other page, index excluded)")
inbound = collections.Counter()
for k, v in pages.items():
    for l in v["links"]:
        t = l.strip()
        if t != k:
            inbound[t] += 1
orphans = sorted(k for k in content if inbound[k] == 0)
in_index = pages["index"]["text"]
for o in orphans:
    listed = "in index" if f"{o}.md)" in in_index else "NOT in index"
    print(f"  {o}  ({listed})")
print(f"  TOTAL: {len(orphans)}")

# ── 4. frontmatter gaps ─────────────────────────────────────────────────────
head("4. FRONTMATTER GAPS")
gaps = {}
for k, v in sorted(content.items()):
    miss = [f for f in REQUIRED_FM if f not in v["fm"]]
    cat = v["fm"].get("category")
    if cat in ("strategy", "analysis") and "timeframe" not in v["fm"]:
        miss.append("timeframe(required for strategy/analysis)")
    if cat == "entity" and "bias" not in v["fm"]:
        miss.append("bias(required for entity)")
    if miss:
        gaps[k] = miss
for k, m in list(gaps.items())[:30]:
    print(f"  {k}: missing {', '.join(m)}")
if len(gaps) > 30:
    print(f"  ... and {len(gaps)-30} more")
print(f"  TOTAL pages with gaps: {len(gaps)} / {len(content)}")

# ── 5. stale ────────────────────────────────────────────────────────────────
head("5. STALE PAGES (updated 30+ days ago)")
stale = []
for k, v in content.items():
    u = v["fm"].get("updated", "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", u)
    if m:
        d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        age = (TODAY - d).days
        if age >= 30:
            stale.append((age, k))
for age, k in sorted(stale, reverse=True)[:20]:
    print(f"  {age:>3}d  {k}")
print(f"  TOTAL: {len(stale)} pages 30+ days old "
      f"(oldest {max(stale)[0] if stale else 0}d)")

# ── 6. schema: missing required sections ────────────────────────────────────
head("6. SCHEMA — MISSING REQUIRED SECTIONS")
sec_missing = {}
for k, v in sorted(content.items()):
    cat = v["fm"].get("category")
    req = SECTIONS.get(cat)
    if not req:
        continue
    hs = " || ".join(v["headings"]).lower()
    miss = [s for s in req if s.split(" / ")[0].lower() not in hs]
    if miss:
        sec_missing[k] = miss
shown = 0
for k, m in sec_missing.items():
    if shown < 25:
        print(f"  {k} [{pages[k]['fm'].get('category')}]: {', '.join(m)}")
        shown += 1
if len(sec_missing) > 25:
    print(f"  ... and {len(sec_missing)-25} more")
print(f"  TOTAL: {len(sec_missing)} pages missing >=1 required section")

# ── 7. sources: N vs listed sources ─────────────────────────────────────────
head("7. FRONTMATTER `sources: N` vs entries under the Sources section")
mismatch = []
for k, v in sorted(content.items()):
    try:
        n = int(v["fm"].get("sources", "0") or 0)
    except ValueError:
        continue
    m = re.search(r"^##+\s*Sources\s*$(.*?)(?=^##\s|\Z)", v["text"], re.M | re.S)
    if not m:
        continue
    body = m.group(1)
    listed = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", body, re.M))
    if listed != n:
        mismatch.append((k, n, listed))
for k, n, l in mismatch[:22]:
    print(f"  {k}: frontmatter says {n}, lists {l}")
if len(mismatch) > 22:
    print(f"  ... and {len(mismatch)-22} more")
print(f"  TOTAL: {len(mismatch)}")

# ── 8. index coverage ───────────────────────────────────────────────────────
head("8. PAGES ON DISK BUT NOT IN index.md")
notlisted = [k for k in sorted(content) if f"{k}.md)" not in in_index]
for k in notlisted:
    print(f"  {k}")
print(f"  TOTAL: {len(notlisted)}")

# ── 9. stale-claim smells ───────────────────────────────────────────────────
head("9. POSSIBLY STALE CLAIMS (phrases that go false when code ships)")
pats = [r"no Python port", r"not (?:yet )?implemented", r"not implemented",
        r"zero occurrences", r"never been measured", r"un-?ported",
        r"needs? an intraday store", r"nothing persists", r"cannot be tested",
        r"blocked on", r"no live example", r"no live-ticker example"]
hits = collections.defaultdict(list)
for k, v in content.items():
    for pat in pats:
        for m in re.finditer(pat, v["text"], re.I):
            s = v["text"][max(0, m.start()-60):m.end()+60].replace("\n", " ")
            hits[k].append(f"…{s.strip()}…")
for k in sorted(hits)[:14]:
    print(f"  {k}:")
    for s in hits[k][:2]:
        print(f"      {s[:150]}")
print(f"  TOTAL: {len(hits)} pages carry at least one such phrase")


# ── 10. --fix-index: COMPUTE the counters instead of trusting them ──────────
#
# The index's own convention comment has said this since 2026-08-07:
#
#     "A lint should COMPUTE both rather than trust them."
#
# It never did, and B-27 stayed open. The counters are written by hand in TWO
# places -- the frontmatter and the body's `_Last updated: ... | Pages: N ...`
# line -- which is precisely how they drifted to two DIFFERENT wrong numbers
# before. Found again on 2026-09-16: the frontmatter said `updated: 2026-09-09`
# while the body said `_Last updated: 2026-09-14_`, and both said 289 against an
# actual 294.
#
# Two hand-maintained copies of one fact is not a counting problem, it is a
# second source of truth. This writes both from the same computed values, so
# they can no longer disagree with each other OR with the vault.
#
# Reporting stays the default: `--fix-index` is opt-in because it edits the vault.
def _fix_index() -> int:
    idx_path = ROOT / "index.md"
    txt = io.open(idx_path, encoding="utf-8").read()
    n_pages, n_src = len(content), src_pages
    today = TODAY.isoformat()

    new, subs = txt, 0
    for pat, rep in (
        (r"(?m)^updated:\s*\d{4}-\d{2}-\d{2}\s*$", f"updated: {today}"),
        (r"(?m)^pages:\s*\d+\s*$", f"pages: {n_pages}"),
        (r"(?m)^sources_ingested:\s*\d+\s*$", f"sources_ingested: {n_src}"),
        (r"_Last updated: \d{4}-\d{2}-\d{2} \| Pages: \d+ \| Sources ingested: \d+_",
         f"_Last updated: {today} | Pages: {n_pages} | Sources ingested: {n_src}_"),
    ):
        new, k = re.subn(pat, rep, new)
        subs += k

    if subs != 4:
        print(f"  !! expected 4 substitutions, made {subs} — index header shape "
              f"changed; NOT written. Fix the shape or this function.")
        return 1
    if new == txt:
        print(f"  index already agrees with the vault "
              f"({n_pages} pages, {n_src} sources, {today})")
        return 0
    io.open(idx_path, "w", encoding="utf-8", newline="\n").write(new)
    print(f"  index rewritten: pages {n_pages}, sources_ingested {n_src}, "
          f"updated {today} — frontmatter AND body line, from one computation")
    return 0


if "--fix-index" in sys.argv:
    head("10. INDEX COUNTERS — COMPUTED AND WRITTEN")
    _fix_index()
