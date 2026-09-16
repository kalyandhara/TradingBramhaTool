"""Tests for wiki_lint's two time-and-encoding defects — B-82.

`wiki_lint.py` runs its whole report at import time, so it cannot be imported
without executing. These drive it as a SUBPROCESS, which is also the only way to
reproduce the bug that started this: it died mid-report on a circled digit
because the Windows console defaults to cp1252, and a tool that quotes prose must
be able to print prose.

The second defect is the one worth keeping. `TODAY` was hardcoded to
`dt.date(2026, 8, 9)` and stayed there for 38 days, so section 5 reported "pages
30+ days old" **as of a date in the past** — drifting further from the truth every
day it was not edited, while every page updated after that date read as a NEGATIVE
age. The lint that exists to find claims which go false with time contained one,
in the single line where time enters it.

Run:  python -m pytest tools/test_wiki_lint.py -q
"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
LINT = HERE / "wiki_lint.py"
VAULT = HERE.parent / "trading-wiki" / "wiki"

pytestmark = pytest.mark.skipif(
    not VAULT.is_dir(), reason="wiki vault not present in this checkout")


def _run(*args, encoding: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if encoding:
        env["PYTHONIOENCODING"] = encoding
    else:
        env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)          # do not let -X utf8 mask the bug
    return subprocess.run([sys.executable, str(LINT), *args],
                          capture_output=True, text=True, timeout=300,
                          encoding="utf-8", errors="replace", env=env)


def test_it_runs_to_completion():
    r = _run()
    assert r.returncode == 0, r.stderr[-800:]
    assert "9. POSSIBLY STALE CLAIMS" in r.stdout, "report stopped early"


def test_it_survives_a_cp1252_console():
    """THE bug: it died on a non-cp1252 character while quoting a page title.

    The vault is full of em dashes and arrows, so this is not hypothetical — it is
    what happens on this machine without `-X utf8`.
    """
    r = _run(encoding="cp1252")
    assert r.returncode == 0, r.stderr[-800:]
    assert "UnicodeEncodeError" not in r.stderr
    assert "9. POSSIBLY STALE CLAIMS" in r.stdout


def test_today_is_todays_date_not_a_frozen_one():
    """If this fails, someone pinned the date again and every staleness number
    below it is measured against the wrong day."""
    r = _run()
    m = re.search(r"WIKI LINT — (\d{4}-\d{2}-\d{2})", r.stdout)
    assert m, r.stdout[:300]
    assert m.group(1) == dt.date.today().isoformat()


def test_no_page_reports_a_negative_age():
    """The symptom a frozen TODAY produces: a page updated after the pinned date
    reads as "-27d old". Ages are durations and cannot be negative."""
    r = _run()
    section = r.stdout.split("5. STALE PAGES", 1)[-1].split("=" * 20, 1)[0]
    assert not re.search(r"^\s*-\d+d\s", section, re.M), section[:400]


def test_the_root_is_derived_from_the_file_not_typed():
    """It was an absolute path to one machine, and a lint nobody else can run is
    a lint that only ever gets run here."""
    src = LINT.read_text(encoding="utf-8")
    assert "pathlib.Path(__file__)" in src
    assert "C:\\Users\\Owner" not in src.split("TODAY")[0]


# ── the index counters ───────────────────────────────────────────────────────

def test_the_index_header_agrees_with_the_vault():
    """`--fix-index` has been run, so this is the steady state. It drifts the
    moment a page is added without rerunning it, which is the point of having a
    check rather than a convention."""
    r = _run()
    line = next((l for l in r.stdout.splitlines() if "index says pages" in l), "")
    assert line, r.stdout[:400]
    assert "MISMATCH" not in line, line


def test_fix_index_is_idempotent_and_reports_when_nothing_changes():
    r = _run("--fix-index")
    assert r.returncode == 0
    assert "10. INDEX COUNTERS" in r.stdout
    r2 = _run("--fix-index")
    assert "already agrees with the vault" in r2.stdout, r2.stdout[-400:]


def test_both_copies_of_the_counter_agree():
    """The counter is written in TWO places — frontmatter and the body's
    `_Last updated: … | Pages: N …` line. They drifted to two different wrong
    numbers before (B-27), and again on 2026-09-16 with two different DATES."""
    txt = (VAULT / "index.md").read_text(encoding="utf-8")
    fm = re.search(r"(?m)^pages:\s*(\d+)\s*$", txt)
    body = re.search(r"_Last updated: (\d{4}-\d{2}-\d{2}) \| Pages: (\d+) \| "
                     r"Sources ingested: (\d+)_", txt)
    assert fm and body, "index header shape changed"
    assert fm.group(1) == body.group(2), "the two page counters disagree"

    fm_date = re.search(r"(?m)^updated:\s*(\d{4}-\d{2}-\d{2})\s*$", txt)
    assert fm_date and fm_date.group(1) == body.group(1), "the two dates disagree"

    fm_src = re.search(r"(?m)^sources_ingested:\s*(\d+)\s*$", txt)
    assert fm_src and fm_src.group(1) == body.group(3)


def test_the_page_counter_matches_what_is_on_disk():
    """`pages` counts every .md under wiki/ EXCLUDING the three meta files — the
    convention stated in index.md's own comment."""
    txt = (VAULT / "index.md").read_text(encoding="utf-8")
    claimed = int(re.search(r"(?m)^pages:\s*(\d+)\s*$", txt).group(1))
    actual = len([p for p in VAULT.rglob("*.md")
                  if p.stem not in {"index", "log", "overview"}])
    assert claimed == actual

    claimed_src = int(re.search(r"(?m)^sources_ingested:\s*(\d+)\s*$", txt).group(1))
    assert claimed_src == len(list((VAULT / "sources").glob("*.md")))
