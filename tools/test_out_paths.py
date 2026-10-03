"""Tests for where generated files go — B-88.

The repo root held 30 `.xlsx`, 19 sector-rotation renders and 5 `.csv`, all
gitignored and all generated. The tidy-up is not a one-line move, because **the
dashboard reads them back** by glob. Changing only the writers would leave a year
of exports invisible to the surface that lists them — a clean-up that silently
deletes history from the reader's point of view is worse than the mess.

So: new files go to `output/`, readers search `output/` AND the root, and nothing
is moved or deleted. These tests pin that both halves hold.

Run:  python -m pytest tools/test_out_paths.py -q
"""
from __future__ import annotations

import importlib
import pathlib

import pytest

import out_paths


@pytest.fixture
def paths(tmp_path, monkeypatch):
    """`out_paths` rebound onto a temp tree, so no test writes into the repo."""
    monkeypatch.setenv("TB_OUT_DIR", str(tmp_path / "output"))
    mod = importlib.reload(out_paths)
    monkeypatch.setattr(mod, "LEGACY_DIR", tmp_path / "legacy")
    (tmp_path / "legacy").mkdir()
    yield mod
    monkeypatch.delenv("TB_OUT_DIR", raising=False)
    importlib.reload(out_paths)


def _touch(d: pathlib.Path, *names: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / n).write_text("x", encoding="utf-8")


# ── writing ──────────────────────────────────────────────────────────────────

def test_out_path_creates_the_directory_on_first_use(paths):
    assert not paths.OUT_DIR.exists()
    p = paths.out_path("screener_20260916.xlsx")
    assert paths.OUT_DIR.is_dir()
    assert p.parent == paths.OUT_DIR


def test_nothing_is_ever_written_to_the_legacy_root(paths):
    paths.out_path("a.xlsx")
    assert list(paths.LEGACY_DIR.iterdir()) == []


# ── reading: the half that makes the move safe ───────────────────────────────

def test_files_already_in_the_root_stay_visible(paths):
    """The whole point. A year of exports must not vanish from the surface that
    lists them just because new ones land elsewhere."""
    _touch(paths.LEGACY_DIR, "sector_rotation_20260801.xlsx",
           "sector_rotation_20260802.xlsx")
    found = paths.find("sector_rotation_*.xlsx")
    assert [p.name for p in found] == ["sector_rotation_20260802.xlsx",
                                       "sector_rotation_20260801.xlsx"]


def test_both_locations_are_merged_newest_first(paths):
    _touch(paths.LEGACY_DIR, "screener_20260801.xlsx", "screener_20260802.xlsx")
    _touch(paths.OUT_DIR, "screener_20260916.xlsx")
    assert [p.name for p in paths.find("screener_*.xlsx")] == [
        "screener_20260916.xlsx", "screener_20260802.xlsx", "screener_20260801.xlsx"]


def test_sorting_is_by_filename_not_mtime(paths):
    """Every one of these names carries a YYYYMMDD stamp. A file copied or
    restored later would sort wrongly by mtime while its NAME still says exactly
    which session produced it."""
    import os
    import time
    _touch(paths.LEGACY_DIR, "screener_20260101.xlsx", "screener_20260901.xlsx")
    old = paths.LEGACY_DIR / "screener_20260901.xlsx"
    os.utime(old, (time.time() - 86_400 * 365, time.time() - 86_400 * 365))
    assert paths.latest("screener_*.xlsx").name == "screener_20260901.xlsx"


def test_output_wins_when_the_same_name_exists_in_both(paths):
    _touch(paths.LEGACY_DIR, "screener_20260916.xlsx")
    _touch(paths.OUT_DIR, "screener_20260916.xlsx")
    hits = paths.find("screener_*.xlsx")
    assert len(hits) == 1, "a duplicate name must not be listed twice"
    assert hits[0].parent == paths.OUT_DIR


def test_resolve_prefers_output_then_falls_back(paths):
    _touch(paths.LEGACY_DIR, "old.xlsx")
    assert paths.resolve("old.xlsx").parent == paths.LEGACY_DIR
    _touch(paths.OUT_DIR, "old.xlsx")
    assert paths.resolve("old.xlsx").parent == paths.OUT_DIR


def test_resolve_returns_none_rather_than_a_phantom_path(paths):
    """A `Path` that does not exist is the thing that turns "no export yet" into
    a confusing error three calls later."""
    assert paths.resolve("nope.xlsx") is None


def test_find_is_empty_not_an_error_when_nothing_matches(paths):
    assert paths.find("nothing_*.xlsx") == []
    assert paths.latest("nothing_*.xlsx") is None


def test_a_missing_output_dir_does_not_break_reading(paths):
    """Readers run before anything has ever been written."""
    _touch(paths.LEGACY_DIR, "screener_20260801.xlsx")
    assert not paths.OUT_DIR.exists()
    assert len(paths.find("screener_*.xlsx")) == 1


def test_directories_matching_the_pattern_are_skipped(paths):
    (paths.LEGACY_DIR / "screener_20260801.xlsx").mkdir()
    assert paths.find("screener_*.xlsx") == []


# ── the writers actually use it ──────────────────────────────────────────────

@pytest.mark.parametrize("mod,needle", [
    ("screener_pipeline", 'out_path(f"screener_'),
    ("sector_rotation", 'out_path(\n        f"sector_rotation_'),
    ("multibagger_candidates", 'out_path(f"multibagger_candidates_'),
    ("promoter_profit_surprise", 'out_path(f"promoter_profit_surprise_'),
])
def test_writers_route_through_out_paths(mod, needle):
    src = (pathlib.Path(__file__).resolve().parent / f"{mod}.py").read_text(
        encoding="utf-8")
    assert needle in src, f"{mod} no longer writes via out_paths"


def test_no_writer_still_targets_the_repo_root():
    """A new dated file written to BASE_DIR is the clutter coming back."""
    here = pathlib.Path(__file__).resolve().parent
    offenders = []
    for name in ("screener_pipeline", "sector_rotation", "multibagger_candidates",
                 "promoter_profit_surprise", "nse_shareholding_fetch",
                 "dashboard_app"):
        for line in (here / f"{name}.py").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            if 'BASE_DIR / f"' in s and any(
                    k in s for k in (".xlsx", ".csv", ".html", ".png")):
                offenders.append(f"{name}: {s[:80]}")
    assert not offenders, offenders
