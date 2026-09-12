"""Tests for svp_screen.py — the READ side of the SVP screen file.

Two things carry the design and both are about restraint rather than cleverness:

  * the history must read OLDEST → NEWEST, because the runner writes it that way
    and a walk printed backwards is a confident lie about which week was last;
  * the measured-negative composite must stay unread. `sig_dir`, `sig_conf`,
    `agreement`, `bull_w` and `bear_w` are not in SAFE_COLUMNS, and a test keeps
    them out — this is the one file where a well-meaning "why not show the
    score too?" would reverse a recorded decision.
"""
import io

import pandas as pd
import pytest

import svp_screen as svp


def _csv(tmp_path, rows):
    p = tmp_path / "svp_screen.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


# ── the history string ────────────────────────────────────────────────────────

def test_history_keeps_the_last_n_oldest_first():
    """The runner writes sessions oldest→newest, so the LAST character is the
    most recent week and the tail is the recent history."""
    assert svp.history("DBBPDDDPDBBB", weeks=8) == "D D D P D B B B"


def test_history_defaults_to_eight_weeks():
    out = svp.history("DBBPDDDPDBBB")
    assert len(out.split()) == 8 == svp.HISTORY_WEEKS


def test_a_short_sequence_is_returned_whole_not_padded():
    """Padding would invent weeks. The cell's length says how much exists."""
    assert svp.history("DBP") == "D B P"


def test_empty_is_none_not_an_empty_string():
    """None distinguishes 'no structure on file' from 'structure that is blank'."""
    assert svp.history("") is None
    assert svp.history(None) is None
    assert svp.history("   ") is None


def test_unknown_characters_are_dropped_rather_than_shown():
    assert svp.history("D-B?P") == "D B P"


def test_every_shape_letter_has_a_meaning_for_the_tooltip():
    for ch in "DBPI":
        assert ch in svp.SHAPE_MEANING and svp.SHAPE_MEANING[ch]


# ── what the loader will and will not read ────────────────────────────────────

def test_the_measured_negative_composite_is_not_in_the_safe_columns():
    """Measured 2026-08-29: corr -0.041, deciles non-monotonic, 5 of 7 factor
    families sign-inverted. The SVP page hides the score and direction; this
    module must not quietly put them back on the main tables."""
    for banned in ("sig_dir", "sig_conf", "agreement", "bull_w", "bear_w",
                   "sig_target", "sig_kind"):
        assert banned not in svp.SAFE_COLUMNS


def test_load_reads_only_the_safe_columns(tmp_path):
    p = _csv(tmp_path, [{
        "symbol": "AAA", "asof": "2026-09-08", "grain": "week", "n_sessions": 12,
        "shape_seq": "DBBPDDDPDBBB", "last_shape": "B", "va_state": "inside_va",
        "n_factors": 5,
        # present in the real file, must not survive the read
        "sig_dir": "BUY", "sig_conf": "high", "agreement": 100, "bull_w": 9,
    }])
    s = svp.load(p)
    assert s["n"] == 1
    row = s["rows"]["AAA"]
    assert row["n_factors"] == 5
    for banned in ("sig_dir", "sig_conf", "agreement", "bull_w"):
        assert banned not in row


def test_load_precomputes_the_history_cell(tmp_path):
    p = _csv(tmp_path, [{"symbol": "AAA", "shape_seq": "DBBPDDDPDBBB",
                         "n_factors": 3}])
    s = svp.load(p)
    assert s["rows"]["AAA"]["svp_hist_8w"] == "D D D P D B B B"


def test_a_missing_file_yields_nothing_rather_than_a_column_of_blanks(tmp_path):
    s = svp.load(tmp_path / "nope.csv")
    assert s["rows"] == {} and s["n"] == 0 and s["age_hours"] is None


def test_the_asof_RANGE_is_reported_not_just_the_file_time(tmp_path):
    """The file's mtime says when the CSV was written; `asof` says which bar each
    row describes. They diverge the moment the screen is extended with freshly
    downloaded names on top of older ones, and then the mtime flatters the old
    rows — which is the whole staleness hazard, inverted."""
    p = _csv(tmp_path, [
        {"symbol": "OLD", "asof": "2026-09-04", "shape_seq": "DDDD", "n_factors": 1},
        {"symbol": "NEW", "asof": "2026-09-10", "shape_seq": "BBBB", "n_factors": 2},
    ])
    s = svp.load(p)
    assert s["asof_min"] == "2026-09-04"
    assert s["asof_max"] == "2026-09-10"
    assert s["asof_spread"] == 2          # a mixed file says so


def test_load_reports_the_file_age_because_staleness_is_the_hazard(tmp_path):
    p = _csv(tmp_path, [{"symbol": "AAA", "shape_seq": "DDDD", "n_factors": 1}])
    s = svp.load(p)
    assert s["age_hours"] is not None and s["age_hours"] >= 0


def test_symbols_are_matched_upper_and_stripped(tmp_path):
    p = _csv(tmp_path, [{"symbol": " aaa ", "shape_seq": "DBPD", "n_factors": 2}])
    s = svp.load(p)
    assert "AAA" in s["rows"]
    assert svp.cells("aaa", s)["svp_factors"] == 2


# ── the cells ─────────────────────────────────────────────────────────────────

def test_a_symbol_outside_the_screen_gets_empty_cells(tmp_path):
    p = _csv(tmp_path, [{"symbol": "AAA", "shape_seq": "DBPD", "n_factors": 2}])
    s = svp.load(p)
    assert svp.cells("NOTINFILE", s) == {"svp_hist_8w": "", "svp_factors": None}


def test_cells_survive_a_junk_factor_count(tmp_path):
    p = _csv(tmp_path, [{"symbol": "AAA", "shape_seq": "DBPD", "n_factors": "n/a"}])
    s = svp.load(p)
    assert svp.cells("AAA", s)["svp_factors"] is None


def test_cells_on_an_empty_screen_do_not_raise():
    assert svp.cells("AAA", {}) == {"svp_hist_8w": "", "svp_factors": None}
    assert svp.cells("AAA", {"rows": {}})["svp_factors"] is None
