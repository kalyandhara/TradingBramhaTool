#!/usr/bin/env python3
"""claims_lint.py — find claims in CODE that went false when a measurement landed.

The sibling of `wiki_lint.py` section 9. That one checks the wiki for phrases
that go stale when code ships; this one checks the code for phrases and figures
that go stale when a BACKTEST ships. Both failures are the same shape and neither
is caught by tests, because a docstring cannot fail.

Why this exists (2026-09-06). The Hidden Treasures caption advertised
"+2.5% @60d (p=0.22)" for a day after B-34r4 retracted exactly that number as a
drifting-window artefact. Sweeping for the cause turned up two more:
`smallcap_discovery` still opened with "UNMEASURED ... until then it's a
discovery lens", after the study had run three times; and `gamma_exposure` still
described itself as a vol-regime input next to the RISK-ON/RISK-OFF gate, after
B-44r retired GEX outright. All three were prose written BEFORE a measurement and
never revisited AFTER it. The wiki gets updated because updating it is the
deliverable. Code headers and captions do not, because nothing points at them
when a result lands.

Three checks:

  0. STATE LABELS — a scanner whose description says "Unmeasured." while a
     verdict file for that exact scanner sits in `cache/b19_verdicts/`. This is
     the class checks 1 and 2 are blind to BY DESIGN, and it took ten stale
     descriptions to notice. See the note above CHECK 3 below.

  1. PROMISES  — "unmeasured", "until then", "needs a backtest". These are
     promissory notes. Each one is either still true or was quietly paid off
     somewhere else, and the file is the last to know.

  2. FIGURES   — p-values, percentage edges and pp deltas sitting in string
     literals and comments. These are the dangerous ones: a number reads as
     authoritative in a way a hedge does not, so a superseded figure is trusted
     more than a stale promise. Every hit must be checked against
     analyses/Open-Backlog.md by a human. The lint cannot know which run is
     current; it can only refuse to let the number go unexamined.

── The design decision that makes this usable ────────────────────────────────
It parses with `ast` and `tokenize` rather than grepping lines, so it sees only
string constants and comments. A raw grep for `0\\.[0-9]+` on dashboard_app.py
returns ~40 hits, nearly all `st.number_input(..., step=0.5)` and slider bounds
— noise that would train you to ignore the output. Scanning only prose drops
those to zero without a single exclusion pattern.

── Suppression, and why it is deliberately annoying ──────────────────────────
A line ending in a `# claims-lint: checked <ref>` comment is skipped, where
<ref> names the backlog item the figure was verified against (e.g. B-34r4).
There is no bare `# noqa`-style silencer: suppressing a figure REQUIRES naming
what you checked it against, because "I looked at it once" is the state that
produced the bug this file exists to catch. For a multi-line or implicitly
concatenated string, the marker counts anywhere inside it.

Run: `python tools/claims_lint.py`          (whole tools/ tree)
     `python tools/claims_lint.py FILE ...` (specific files)

Exit 0 always. This reports, it does not fix and it does not gate a commit —
same principle as wiki_lint's `sources: N` mismatch: a number rewritten
confidently by a script that cannot read the backlog would be worse than the
stale one it replaced.
"""
from __future__ import annotations
import ast
import io
import pathlib
import re
import sys
import tokenize

HERE = pathlib.Path(__file__).resolve().parent

#: Promissory phrases — prose that dates itself the moment a study is run.
#: NOT matched, on purpose: bare "unmeasured" and "unvalidated". This repo uses
#: both as honest STATE LABELS — "the ownership leg stays unmeasured", "it lands
#: in no family and is scored as unmeasured, the honest default" — and the first
#: run of this lint returned ~40 such lines, every one of them correct. A lint
#: that is mostly right is one you learn to skim, which is the failure mode this
#: file exists to prevent. What dates itself is the PROMISE of future work, not
#: the admission of present ignorance, so only promissory forms appear below.
PROMISES = [
    r"until then\b",
    r"not (?:yet )?(?:been )?measured",
    r"never been measured",
    r"needs? (?:a )?(?:backtest|measuring|measurement)",
    r"awaiting measurement",
    r"every weight (?:below |here )?is a prior",
    r"to be measured",
    r"TODO:? measure",
    r"has (?:not|never) (?:yet )?(?:gone |been )through",
    r"once (?:this|it) (?:is|has been) measured",
    # "unbacktested" IS matched where bare "unmeasured" is not, and the difference
    # is real: "unmeasured" is used here as a state label for a thing nobody
    # intends to measure, while "unbacktested" names a specific pending test and
    # goes false the day it runs. It appears twice in the tree, so it is nearly
    # free. Added 2026-09-06 after session_volume_profile.js carried
    # "unbacktested" for eight days past its own measurement — extending this lint
    # to .js was necessary to see the file, and this pattern was necessary to
    # flag the line.
    r"\bun-?backtested\b",
]

#: A REPORTED p-value is never anything but a claim about a measurement, so
#: these match unconditionally.
#:
#: `=` only, deliberately NOT `<` or `≤`. Widening to `p<0.05` pulled in ~15
#: lines on the 2026-09-06 tightening pass, and every one was a table legend
#: ("* = Welch p<0.05 vs baseline") or a PRE-REGISTERED pass bar ("promote only
#: if lift >= 1.3 AND p < 0.01"). Those are the opposite of a stale claim: a
#: threshold set before the run cannot be invalidated by the result, and
#: pre-registration is the practice this desk is trying to keep. An inequality
#: states a rule; an equality states an outcome. Only outcomes go stale.
#:
#: A result written with ≤ (opportunity_daily's "−1 to −2.2%, p≤0.05") is not
#: lost — it still surfaces through its percentage under the contextual rules.
FIGURES_ALWAYS = [
    r"\bp ?= ?0?\.\d+",
    r"\bp_rot\b ?[=:] ?0?\.\d+",
    r"\bhit rate of \d",
    r"\b\d+\.\d+ ?% @ ?\d+ ?d\b",
]

#: A bare percentage or pp figure is ambiguous — as likely to be a threshold, a
#: Fibonacci level, or a worked rendering example as a result. These match ONLY
#: with measurement vocabulary nearby (CONTEXT) and no disqualifying shape in
#: the window (FIGURE_EXCLUDE).
FIGURES_CONTEXTUAL = [
    r"[+\-−]\d+\.\d+ ?%",
    r"[+\-−]?\d+\.\d+ ?pp\b",
]

#: Vocabulary that turns a number into a claim about the future: horizons
#: ("@60d", "at 5/10/20d"), significance, and the words this desk reaches for
#: when it reports a study.
CONTEXT = re.compile(
    r"\bp ?[=≤<] ?0?\.\d"
    r"|\bp_rot\b|\bwelch\b|\brotation\b"
    r"|@ ?\d+ ?d\b|\bat \d+(?:/\d+)+ ?d\b"
    r"|\bedge\b|\blift\b|\balpha\b|\bhit rate\b|\bhit%"
    r"|\bbacktest\b|\bharness\b|\bforward\b|\bbaseline\b"
    r"|\bmeasured\b|\bsignifican|\btercile\b|\bmedian\b|\bp25\b|\bp75\b"
    r"|\bper trade\b|\bquantile\b|\bB-\d+",
    re.I,
)

#: Shapes that carry measurement vocabulary by coincidence and still are not
#: claims. Every one was a real false positive on the 2026-09-06 first run:
#: `-0.00%` in two modules arguing how a flat day should RENDER; peer_comparison
#: and dashboard_app quoting "-3.2%" as example formatter output; ew_module's
#: 38.2-61.8% Fibonacci retracement zone; scanner_templates' ">= -0.1%" slope
#: floor. Prose about numbers, and constants that were never measured.
FIGURE_EXCLUDE = re.compile(
    r"[+\-−]?0\.00 ?%"
    r"|\b(?:23\.6|38\.2|50\.0|61\.8|78\.6)\b"
    r"|[≥≤><]=? ?[+\-−]?\d+\.\d+ ?%"
    r"|\brenders?\b|\brendering\b|\bformatter\b|\bformat(?:ted|s)?\b",
    re.I,
)

SUPPRESS = re.compile(r"#\s*claims-lint:\s*checked\s+\S+")


#: Non-Python files are scanned as PLAIN TEXT (no ast, no tokenize), because the
#: engine-vs-renderer split this lint exists to catch crosses languages. Proved on
#: 2026-09-06: session_volume_profile.js emitted "unbacktested" for eight days
#: after the measurement, and chart_dashboard.html overrode it at the RENDER layer
#: — so the card looked right while the engine lied to every other consumer. A
#: .py-only lint could not see either file.
TEXT_SUFFIXES = (".js", ".html")


def _targets(argv: list[str]) -> list[pathlib.Path]:
    if argv:
        return [pathlib.Path(a).resolve() for a in argv]
    out = [p for p in HERE.glob("*.py") if p.name != "claims_lint.py"]
    for suf in TEXT_SUFFIXES:
        out += list(HERE.glob("*" + suf))
    return sorted(out)


def _prose(path: pathlib.Path) -> list[tuple[int, int, str]]:
    """(lineno, end_lineno, text) for every string constant and comment.

    Docstrings and ordinary string literals come from the AST; comments come
    from tokenize, because the AST discards them. Anything that is not prose —
    slider bounds, thresholds, numeric defaults — never appears here, which is
    the whole point.
    """
    src = io.open(path, encoding="utf-8").read()
    out: list[tuple[int, int, str]] = []
    if path.suffix.lower() in TEXT_SUFFIXES:
        # Whole-file, line by line. Cruder than the Python path — a JS string and
        # a JS comment look alike here — but the alternative is a JS parser to
        # save a few false positives, and a false positive costs one glance.
        for i, line in enumerate(src.splitlines(), 1):
            out.append((i, i, line))
        return out
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        print(f"  !! {path.name}: does not parse ({exc.msg} line {exc.lineno}) — skipped")
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.end_lineno or node.lineno, node.value))
    try:
        with io.open(path, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.COMMENT:
                    out.append((tok.start[0], tok.start[0], tok.string))
    except tokenize.TokenError:
        pass
    return out


def _suppressed(path: pathlib.Path) -> set[int]:
    """Line numbers carrying a `# claims-lint: checked <ref>` marker."""
    lines = io.open(path, encoding="utf-8").read().splitlines()
    return {i for i, ln in enumerate(lines, 1) if SUPPRESS.search(ln)}


def _scan(paths: list[pathlib.Path], pats: list[str],
          gated: bool = False) -> list[tuple[str, int, str]]:
    """Report (file, line, snippet) for each pattern hit.

    With ``gated``, a hit survives only if its ±55-char window carries
    measurement vocabulary (CONTEXT) and no disqualifying shape
    (FIGURE_EXCLUDE). The window, not the whole string, is the unit: a long
    docstring will mention a horizon somewhere, and judging a number by
    something 40 lines away is how a filter stops filtering.
    """
    rx = [re.compile(p, re.I) for p in pats]
    found: list[tuple[str, int, str]] = []
    for path in paths:
        if not path.exists():
            print(f"  !! {path} does not exist — skipped")
            continue
        skip = _suppressed(path)
        for lineno, end, text in _prose(path):
            # A marker anywhere in the string's span suppresses it. Implicit
            # concatenation - which is how every long caption in dashboard_app
            # is written - reports only its FIRST line to the AST, so demanding
            # the marker there would mean counting lines to silence a hit. That
            # is friction in the wrong place: the marker is meant to be easy to
            # add and hard to add HONESTLY, and only the second half matters.
            if any(n in skip for n in range(lineno, end + 1)):
                continue
            for r in rx:
                m = r.search(text)
                if not m:
                    continue
                lo = max(0, m.start() - 55)
                window = text[lo:m.end() + 55]
                if gated and (not CONTEXT.search(window)
                              or FIGURE_EXCLUDE.search(window)):
                    continue
                snip = re.sub(r"\s+", " ", window.replace("\n", " ")).strip()
                found.append((path.name, lineno, snip))
                break
    return found


#: CHECK 3 — a STATE LABEL that was true when written and silently became false.
#:
#: The PROMISES list above explains, at length, why bare "unmeasured" is not
#: matched: this repo uses it as an honest state label and flagging it produced
#: ~40 correct lines. That reasoning was right and still is.
#:
#: What it missed is that the label is CHECKABLE when its subject is a named
#: scanner, because `cache/b19_verdicts/` is ground truth: a verdict file exists
#: if and only if B-19 measured that scanner. No vocabulary heuristic, no window,
#: no judgement — a name either has a verdict or it does not.
#:
#: Found 2026-09-11 the expensive way. `Liquidity Sweep` ended its description
#: with "Unmeasured." while B-41m had measured it at +0.51% @20d (p=0.005), the
#: only edge on this desk that survives costs. Checking the other eight found ALL
#: EIGHT stale too — B-19 measured every one on 2026-09-02 and nobody went back to
#: the text. The worst was `Support Breakdown`, a RISK flag measured at +0.47%
#: @20d / +1.22% @60d, i.e. pointing the wrong way, described as "Unmeasured."
#:
#: This check has no false-positive rate to tune. If it ever fires wrongly, the
#: verdict file is misnamed, which is worth knowing too.
#:
#: SCOPE. Two sources, and they cover different halves:
#:   * `cache/b19_verdicts/` — one file per scanner from the B-19 batch.
#:   * `named_studies.STUDIES` — the index of every OTHER measurement, built
#:     2026-09-11 because B-41m measured `Liquidity Sweep` through the shared
#:     harness and left nothing on disk to associate the two. That is why its
#:     stale label had to be found by hand.
#: The index reports its own coverage gaps (CHECK 0b), so a study that is not
#: indexed is visible rather than silently uncheckable.
STATE_LABEL = re.compile(r"\bunmeasured\b|\bunvalidated\b|\bnot (?:yet )?measured\b", re.I)

VERDICT_DIR = HERE / "cache" / "b19_verdicts"


def _scanner_descriptions(path: pathlib.Path | None = None) -> list[tuple[str, int, str]]:
    """(name, lineno, description) for every entry in scanner_templates.SCANNERS.

    Parsed with `ast` rather than imported, for the same reason the rest of this
    file parses: importing scanner_templates costs pandas/numpy and can fail for
    reasons that have nothing to do with linting prose. Implicitly concatenated
    string literals — which is how every long description is written — fold into a
    single Constant, so they read back whole.
    """
    path = path or HERE / "scanner_templates.py"
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        # BOTH forms, and the annotated one is the one that matters: the real
        # registry is written `SCANNERS: dict[str, dict] = {`, which is an
        # AnnAssign and NOT an Assign. Handling only Assign made this function
        # return zero descriptions from the only file it exists to read, while
        # the synthetic test fixture (a plain `SCANNERS = {`) passed. The check
        # reported "(none)" and that looked exactly like success.
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            continue
        if not (any(getattr(t, "id", None) == "SCANNERS" for t in targets)
                and isinstance(node.value, ast.Dict)):
            continue
        for key, val in zip(node.value.keys, node.value.values):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                continue
            if not isinstance(val, ast.Dict):
                continue
            for k2, v2 in zip(val.keys, val.values):
                if (isinstance(k2, ast.Constant) and k2.value == "description"
                        and isinstance(v2, ast.Constant) and isinstance(v2.value, str)):
                    out.append((key.value, key.lineno, v2.value))
    return out


def _verdict_line(name: str, vdir: pathlib.Path | None = None) -> str | None:
    """The scanner's row from the B-19 summary table, so the fix is one paste."""
    table = (vdir or VERDICT_DIR) / "_summary_table.txt"
    if not table.exists():
        return None
    for line in table.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(name + " ") or line.startswith(name + "	"):
            return re.sub(r"\s+", " ", line).strip()
    return None


def _named_by_subject() -> dict[str, list[dict]]:
    """The named-study index, or {} if it is unavailable.

    Imported lazily and defensively: this lint must keep working on a tree where
    `named_studies` is missing or broken, because a lint that dies is a lint that
    gets removed from the habit.
    """
    try:
        import named_studies
        return named_studies.by_subject()
    except Exception:
        return {}


def _scan_uncovered_studies() -> list[tuple[str, int, str]]:
    """Study files that the named-study index does not claim.

    Not a stale claim — a BLIND SPOT. Each of these is a measurement whose result
    the lint cannot cross-reference against anything, which is the state every
    named study was in before 2026-09-11.
    """
    try:
        import named_studies
        gaps = named_studies.uncovered_tools()
    except Exception:
        return []
    return [("named_studies.py", 0,
             f"{g} is a study file that no index entry claims — its subjects "
             f"cannot be checked for stale labels") for g in gaps]


def _scan_indicator_evidence() -> list[tuple[str, int, str]]:
    """CHECK 0d — the Indicator Browser's evidence lines vs the study index."""
    try:
        import indicator_evidence as ie
    except Exception as e:                                   # pragma: no cover
        return [("indicator_evidence.py", 0, f"could not import: {e}")]
    return [("indicator_evidence.py", 0, p) for p in ie.self_check()]


def _scan_unrecorded_studies() -> list[tuple[str, int, str]]:
    """Indexed studies with no citable result. Debt, displayed."""
    try:
        import named_studies
        rows = named_studies.unrecorded()
    except Exception:
        return []
    return [("named_studies.py", 0,
             f"{st['item']} ({st['tool']}) is indexed but has NO citable result — "
             f"{st.get('headline') or 'no write-up found'}") for st in rows]


def _scan_state_labels(src: pathlib.Path | None = None,
                       vdir: pathlib.Path | None = None) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    vdir = vdir or VERDICT_DIR
    if not vdir.is_dir():
        return rows
    measured = {f.stem for f in vdir.glob("*.txt") if not f.stem.startswith("_")}
    named = _named_by_subject()
    for name, lineno, desc in _scanner_descriptions(src):
        if not STATE_LABEL.search(desc):
            continue
        if name.replace(" ", "_") not in measured:
            # Not in the B-19 batch — but a NAMED study may still have measured
            # it. This is the half that let `Liquidity Sweep` sit stale for days.
            hits = named.get(name)
            if not hits:
                continue      # label is accurate — nothing measured it
            st = hits[0]
            rows.append(((src or pathlib.Path("scanner_templates.py")).name, lineno,
                         f"{name!r} claims unmeasured, but {st['item']} measured it "
                         f"({st['verdict']}): {st.get('headline') or st['source']}"))
            continue
        verdict = _verdict_line(name, vdir) or "see cache/b19_verdicts/"
        rows.append((( src or pathlib.Path("scanner_templates.py")).name, lineno,
                     f"{name!r} claims unmeasured, but B-19 says: {verdict}"))
    return sorted(rows, key=lambda r: r[1])


#: CHECK 3 — a COUNT in prose that disagrees with a registry the code can count.
#:
#: Found 2026-09-14 (B-79): the Scanner Hub's nav tooltip said "24 pattern
#: scanners" against a registry of 46 — stale since whenever the 25th shipped, and
#: sitting ONE HOVER away from a Home tile that counts `len(sc.SCANNERS)` correctly.
#: Two more copies had drifted the same way in `opportunity_daily`'s docstring.
#:
#: This is the same SHAPE as CHECK 0 and deliberately not like CHECK 2: there is
#: ground truth, so no human judgement is required and the check fires only on a
#: real mismatch. A count that agrees with the registry is silent, so the output
#: is empty in the normal case and every line is definitely wrong — the property
#: that keeps a lint worth reading.
#:
#: WHY MEASUREMENT VOCABULARY DISQUALIFIES A HIT, which is the whole precision
#: story. "0/41 scanners stable after costs" is B-19's RESULT: a true statement
#: about a past run over the 41 scanners that existed then, and it must NOT be
#: rewritten to 46 when the 47th ships. A historical result is not a stale
#: inventory claim, and the CONTEXT vocabulary already separates them — the same
#: regex CHECK 2 uses to decide a number IS a measurement, used here inverted.
#: PRECISION, built the same empirical way as FIGURE_EXCLUDE. The first cut
#: matched "<N> ... scanners|pages" with up to two adjectives between, and
#: returned **14 hits on the real tree, every one wrong**:
#:
#:   "exactly 1 scanner fired" · "at least 2 valid scanner names" ·
#:   "7 scanners · 2 families" · "42 scanners, 114 candidates rated" ·
#:   "trimmed 12 scanners over" · "0.30 x best scanner score" (a DECIMAL read as
#:   a count) · wiki_lint's "4 pages" (wiki pages, a different registry entirely)
#:
#: The lesson is that `scanner` and `page` are among the commonest nouns in this
#: repo, and nearly every number near them counts an EVENT — how many fired, how
#: many were rated, how many a study trimmed — not the inventory. No blacklist of
#: verbs was going to hold.
#:
#: So the check is keyed on noun phrases that only ever denote the WHOLE
#: registry. It catches less and is worth more: the alternative is a check whose
#: output you learn to skim, which is the failure this file exists to prevent.
#: The lookbehind additionally kills `0.30 x` and `0/41`.
COUNT_CLAIMS = [
    (r"(?<![.\d/])\b(\d{1,3})\s+pattern\s+scanners?\b",   "scanner"),
    (r"(?<![.\d/])\bof\s+(\d{1,3})\s+scanners?\b",        "scanner"),
    (r"(?<![.\d/])\b(\d{1,3})\s+sidebar\s+groups?\b",     "group"),
    (r"(?<![.\d/])\b(\d{1,3})\s+pages?\s+across\b",       "page"),
]

#: Noun → (module, symbol, how to count it). Parsed with `ast`, never imported,
#: for the reason the rest of this file parses: importing `dashboard_app` runs a
#: Streamlit app.
COUNT_REGISTRY = {
    "scanner":  ("scanner_templates.py", "SCANNERS", "dict_keys"),
    "page":     ("dashboard_app.py", "PAGE_GROUPS", "sum_of_list_values"),
    "group":    ("dashboard_app.py", "PAGE_GROUPS", "dict_keys"),
}


def _count_symbol(fname: str, symbol: str, how: str) -> int | None:
    """Size of a module-level dict literal, without importing the module."""
    path = HERE / fname
    if not path.exists():
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        # Both plain and annotated assignment — `SCANNERS: dict[str, dict] = {`
        # is an AnnAssign, and handling only Assign is the exact bug recorded
        # above `_scanner_descriptions`.
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            continue
        if not (any(getattr(t, "id", None) == symbol for t in targets)
                and isinstance(node.value, ast.Dict)):
            continue
        if how == "dict_keys":
            return len(node.value.keys)
        if how == "sum_of_list_values":
            total = 0
            for v in node.value.values:
                if isinstance(v, (ast.List, ast.Tuple)):
                    total += len(v.elts)
            return total
    return None


def _scan_count_claims(paths: list[pathlib.Path]) -> list[tuple[str, int, str]]:
    """Prose counts that disagree with what the registry actually holds."""
    actual: dict[str, int | None] = {}
    for noun, (fname, symbol, how) in COUNT_REGISTRY.items():
        actual[noun] = _count_symbol(fname, symbol, how)

    rx = [(re.compile(p, re.I), noun) for p, noun in COUNT_CLAIMS]
    seen: set[tuple[str, int, int, str]] = set()
    rows: list[tuple[str, int, str]] = []
    for path in paths:
        if not path.exists():
            continue
        skip = _suppressed(path)
        for lineno, end, text in _prose(path):
            if any(n in skip for n in range(lineno, end + 1)):
                continue
            for r, noun in rx:
                for m in r.finditer(text):
                    claimed = int(m.group(1))
                    real = actual.get(noun)
                    if real is None or claimed == real:
                        continue
                    lo = max(0, m.start() - 55)
                    window = text[lo:m.end() + 55]
                    if CONTEXT.search(window):
                        continue      # a measurement RESULT, not an inventory claim
                    # Keyed on the NOUN as well as the line: "23 pages across 5
                    # sidebar groups" is two independent claims on one line, and
                    # `_dedupe` (file, line) would silently drop the second.
                    key = (path.name, lineno, claimed, noun)
                    if key in seen:
                        continue
                    seen.add(key)
                    snip = re.sub(r"\s+", " ", window.replace("\n", " ")).strip()
                    rows.append((path.name, lineno,
                                 f"says {claimed} {noun}(s), registry holds "
                                 f"{real} — {snip}"))
    return sorted(rows)


def _dedupe(rows: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """One row per (file, line), keeping the longest snippet.

    Two patterns hitting the same caption at different offsets is the normal
    case — "−0.12% @60d (p=0.94)" matches on the percentage and again on the
    p-value. Reporting it twice makes the total meaningless, and the total is
    the number a person actually reads.
    """
    best: dict[tuple[str, int], tuple[str, int, str]] = {}
    for name, lineno, snip in rows:
        cur = best.get((name, lineno))
        if cur is None or len(snip) > len(cur[2]):
            best[(name, lineno)] = (name, lineno, snip)
    return [best[k] for k in sorted(best)]


def _report(title: str, note: str, rows: list[tuple[str, int, str]]) -> None:
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)
    print(f"  {note}")
    print()
    if not rows:
        print("  (none)")
        return
    for name, lineno, snip in rows:
        print(f"  {name}:{lineno}")
        print(f"      …{snip[:130]}…")
    print()
    print(f"  TOTAL: {len(rows)}")


def main(argv: list[str]) -> int:
    # Windows consoles default to cp1252 and this lint quotes the very prose it
    # scans — arrows, dashes, the warning glyph. Reconfiguring here rather than
    # trusting the caller is the lesson from opportunity_daily, where one
    # unencodable character in a progress line killed a completed 42-scanner run
    # four statements before the save.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    paths = _targets(argv)
    print(f"claims_lint — {len(paths)} file(s) under {HERE}")

    _report(
        "0. STATE LABELS CONTRADICTED BY A MEASUREMENT (no judgement needed)",
        "A scanner describing itself as unmeasured while cache/b19_verdicts/ or "
        "named_studies.STUDIES says otherwise. Unlike the two checks below, every "
        "hit here is definitely wrong — both sources are ground truth. Paste the "
        "numbers into the description.",
        _scan_state_labels(),
    )
    _report(
        "0b. STUDY FILES MISSING FROM THE NAMED-STUDY INDEX (a blind spot, not a "
        "stale claim)",
        "Each is a measurement whose subjects CHECK 0 cannot cross-reference. "
        "Index it in named_studies.STUDIES — item, tool, subjects — and its "
        "scanners become checkable. Expected to be non-empty while the index is "
        "still being filled in.",
        _scan_uncovered_studies(),
    )
    _report(
        "0d. CHART TOOL EVIDENCE LINES OUT OF STEP WITH THE INDEX (B-154)",
        "indicator_evidence.EVIDENCE writes a plain sentence per indicator against a "
        "verdict. A subject renamed out of named_studies, or a study whose verdict "
        "moved, makes that sentence wrong on every beginner's screen. Rewrite the "
        "line and its `expect`.",
        _scan_indicator_evidence(),
    )
    _report(
        "0c. STUDIES THAT RAN AND LEFT NO WRITE-UP (the stale-claim disease, "
        "inverted)",
        "Indexed, subjects known, result not recorded anywhere citable. A "
        "measurement with no write-up is debt; each should gain a source with real "
        "numbers or be retired.",
        _scan_unrecorded_studies(),
    )
    _report(
        "3. COUNTS THAT DISAGREE WITH THE REGISTRY (no judgement needed)",
        "A number in prose that the code can count and that does not match. Like "
        "CHECK 0, every hit is definitely wrong. A measurement RESULT over a past "
        "registry (\"0/41 scanners stable\") is deliberately NOT flagged — it is "
        "true about the run it describes.",
        _scan_count_claims(paths),
    )
    _report(
        "1. PROMISSORY CLAIMS (prose that dates itself when a study runs)",
        "Each is either still true, or was paid off in the backlog and the file "
        "never heard.",
        _scan(paths, PROMISES),
    )
    _report(
        "2. HARDCODED FIGURES (check every one against analyses/Open-Backlog.md)",
        "A number reads as authoritative in a way a hedge does not, so a "
        "superseded figure is trusted MORE than a stale promise. Silence one "
        "with a trailing `# claims-lint: checked B-NNx` naming what you checked "
        "it against.",
        _dedupe(_scan(paths, FIGURES_ALWAYS)
                + _scan(paths, FIGURES_CONTEXTUAL, gated=True)),
    )

    print()
    print("  Nothing here is automatically wrong. This lint cannot read the "
          "backlog and")
    print("  will not guess which run is current — it only refuses to let a "
          "figure go")
    print("  unexamined. Reporting only; exit is always 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
