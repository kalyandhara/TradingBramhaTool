"""Tests for claims_lint's CHECK 0 — the state-label cross-reference.

    py -3 -m pytest tools/test_claims_lint.py -q

This check exists because on 2026-09-11 **ten** scanner descriptions still ended
with the word "Unmeasured." after B-19 had measured every one of them, and the two
existing checks were blind to it BY DESIGN (bare "unmeasured" is an honest state
label elsewhere in this repo, and matching it produced ~40 correct lines).

These tests matter more than usual for one reason: **on the current tree the check
correctly reports (none)**, because the ten were fixed before it was written. A
check that returns nothing is indistinguishable from a check that is broken, so its
positive case has to be proven on synthetic input rather than assumed.
"""

from __future__ import annotations

import pathlib

import pytest

import claims_lint as cl


SRC = '''
SCANNERS = {
    "Alpha Scan": {
        "fn": None,
        "description": (
            "Fires on a thing. Emits entry/stop/target. Unmeasured."
        ),
        "category": "Entry",
    },
    "Beta Scan": {
        "fn": None,
        "description": "A different thing. Unmeasured.",
        "category": "Risk",
    },
    "Gamma Scan": {
        "fn": None,
        "description": "MEASURED (B-19): 400 signals, +0.20% @20d.",
        "category": "Entry",
    },
}
'''


@pytest.fixture
def tree(tmp_path: pathlib.Path):
    src = tmp_path / "scanner_templates.py"
    src.write_text(SRC, encoding="utf-8")
    vdir = tmp_path / "b19_verdicts"
    vdir.mkdir()
    # Alpha was measured; Beta was not. Gamma was, but does not claim otherwise.
    (vdir / "Alpha_Scan.txt").write_text("=== Walk-Forward: Alpha Scan ===", encoding="utf-8")
    (vdir / "Gamma_Scan.txt").write_text("=== Walk-Forward: Gamma Scan ===", encoding="utf-8")
    (vdir / "_summary_table.txt").write_text(
        "Scanner                     Cat      Sig   20d edge   60d edge Verdict\n"
        "Alpha Scan                  Entry    211     +0.36%     +0.93% POSITIVE EDGE\n"
        "Gamma Scan                  Entry    400     +0.20%     +0.10% POSITIVE EDGE\n",
        encoding="utf-8")
    return src, vdir


def test_flags_a_scanner_that_claims_unmeasured_but_has_a_verdict(tree):
    src, vdir = tree
    rows = cl._scan_state_labels(src, vdir)
    names = " ".join(r[2] for r in rows)
    assert "Alpha Scan" in names, "the whole point of the check did not fire"


def test_does_not_flag_a_scanner_with_no_verdict_file(tree):
    """`Beta Scan` says unmeasured and nothing measured it. The label is CORRECT.

    This is the case the older checks were right to stay silent on, and the reason
    this check cross-references instead of matching vocabulary.
    """
    src, vdir = tree
    assert not any("Beta Scan" in r[2] for r in cl._scan_state_labels(src, vdir))


def test_does_not_flag_a_scanner_that_already_reports_its_result(tree):
    src, vdir = tree
    assert not any("Gamma Scan" in r[2] for r in cl._scan_state_labels(src, vdir))


def test_exactly_one_row_on_this_fixture(tree):
    """Guards against a change that makes the check fire on everything."""
    src, vdir = tree
    assert len(cl._scan_state_labels(src, vdir)) == 1


def test_the_verdict_numbers_travel_with_the_finding(tree):
    """The row must carry the B-19 line, so fixing it is a paste and not a hunt."""
    src, vdir = tree
    row = cl._scan_state_labels(src, vdir)[0]
    assert "+0.36%" in row[2] and "POSITIVE EDGE" in row[2]


def test_missing_verdict_dir_is_silent_not_an_error(tmp_path):
    src = tmp_path / "scanner_templates.py"
    src.write_text(SRC, encoding="utf-8")
    assert cl._scan_state_labels(src, tmp_path / "nope") == []


def test_descriptions_parse_without_importing_scanner_templates(tree):
    """Implicitly concatenated literals must read back whole -- that is how every
    long description in the real file is written."""
    src, _ = tree
    got = dict((n, d) for n, _l, d in cl._scanner_descriptions(src))
    assert "Unmeasured." in got["Alpha Scan"]
    assert got["Alpha Scan"].startswith("Fires on a thing")


# ── the real tree ───────────────────────────────────────────────────────────────

def test_the_real_registry_actually_parses():
    """VACUITY GUARD, and it is the whole reason this file exists.

    The first version of the check handled only `ast.Assign`, but the real registry
    is written `SCANNERS: dict[str, dict] = {` -- an **AnnAssign**. So it read ZERO
    descriptions from the only file it guards, reported "(none)", and looked exactly
    like a passing check. The synthetic fixture above used a plain `SCANNERS = {`
    and passed happily.

    A check that reports nothing is indistinguishable from a check that is broken,
    so this asserts the check can still SEE the thing it is checking.
    """
    n = len(cl._scanner_descriptions())
    assert n > 20, f"only {n} scanner descriptions parsed -- the walk went blind again"


def test_real_tree_is_clean():
    """The ten found on 2026-09-11 are fixed and must stay fixed.

    If this fails, a scanner description has gone stale again and the failure
    message names it.
    """
    rows = cl._scan_state_labels()
    assert not rows, "stale state labels: " + "; ".join(r[2] for r in rows)
