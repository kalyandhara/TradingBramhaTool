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

Two checks:

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


def _targets(argv: list[str]) -> list[pathlib.Path]:
    if argv:
        return [pathlib.Path(a).resolve() for a in argv]
    return sorted(p for p in HERE.glob("*.py") if p.name != "claims_lint.py")


def _prose(path: pathlib.Path) -> list[tuple[int, int, str]]:
    """(lineno, end_lineno, text) for every string constant and comment.

    Docstrings and ordinary string literals come from the AST; comments come
    from tokenize, because the AST discards them. Anything that is not prose —
    slider bounds, thresholds, numeric defaults — never appears here, which is
    the whole point.
    """
    src = io.open(path, encoding="utf-8").read()
    out: list[tuple[int, int, str]] = []
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
