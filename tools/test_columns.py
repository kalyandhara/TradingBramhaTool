"""Tests for columns.py (B-63a).

The module's whole value is that a column means ONE thing everywhere. So the
tests pin the rules that keep it that way rather than the contents of any label:

  * an unknown column raises instead of rendering an unexplained header;
  * a caller can adjust layout (label, width) but CANNOT redefine the number
    (format, tooltip) — that is the drift this replaces;
  * aliases resolve to the same spec object, so `day_pct` and `chg_pct` cannot
    say different things;
  * every spec carries a tooltip, because the tooltip is what makes a wide table
    legible and an untooltipped column is how the old mess started.
"""
import pandas as pd
import pytest

import columns as C


def test_every_column_has_a_tooltip():
    missing = [cid for cid, s in C.COLUMNS.items() if not (s.help or "").strip()]
    assert not missing, f"columns without help text: {missing}"


def test_every_number_column_has_a_format():
    missing = [cid for cid, s in C.COLUMNS.items()
               if s.kind == "number" and not s.fmt]
    assert not missing, f"number columns without a format: {missing}"


def test_link_columns_keep_a_word_beside_the_emoji():
    """Emoji-ONLY display_text trips Streamlit's spurious edit-pencil bug — the
    reason the original helper spelled out '👁 Chart' rather than '👁'."""
    for cid in C.CHART_FAMILY:
        s = C.COLUMNS[cid]
        assert s.kind == "link"
        assert any(ch.isalpha() for ch in (s.display_text or ""))


def test_unknown_column_raises_rather_than_rendering_bare():
    with pytest.raises(KeyError):
        C.spec("some_column_nobody_defined")
    assert C.resolve("some_column_nobody_defined") is None


def test_aliases_resolve_to_one_definition():
    # Both spellings were live in the same function, saying different things.
    assert C.resolve("day_pct") == "chg_pct"
    assert C.spec("day_pct") is C.spec("chg_pct")
    assert C.spec("multiple") is C.spec("rvol")


def test_the_two_rvol_bases_stay_separate_ids():
    """A 20-day mean and a 5-session median are not the same number; aliasing
    them would be a silent behaviour change dressed as a refactor."""
    assert C.resolve("rvol_median5") == "rvol_median5"
    assert C.COLUMNS["rvol"] is not C.COLUMNS["rvol_median5"]
    assert "20-day" in C.COLUMNS["rvol"].help
    assert "MEDIAN" in C.COLUMNS["rvol_median5"].help


def test_raw_rupee_turnover_is_not_aliased_to_crore():
    """They differ by 1e7. Aliasing would mislabel one by seven orders."""
    assert "turnover" not in C.ALIASES
    assert C.resolve("turnover") is None


def test_layout_may_be_overridden():
    cfg = C.configure("close", overrides={"close": {"label": "Price", "width": "small"}})
    assert "close" in cfg


def test_the_definition_may_not_be_overridden():
    for bad in ({"fmt": "%.4f"}, {"help": "something else"}, {"kind": "text"}):
        with pytest.raises(ValueError) as e:
            C.configure("close", overrides={"close": bad})
        assert "own id" in str(e.value)


def test_configure_keys_by_the_name_the_caller_passed():
    """A frame whose column is still called day_pct must not need renaming."""
    cfg = C.configure("day_pct", "chg_pct")
    assert set(cfg) == {"day_pct", "chg_pct"}


def test_configure_df_ignores_columns_it_does_not_know():
    df = pd.DataFrame({"symbol": ["X"], "close": [1.0],
                       "something_bespoke": [2]})
    cfg = C.configure_df(df)
    assert set(cfg) == {"symbol", "close"}      # bespoke column left to Streamlit


def test_configure_df_can_add_columns_not_yet_in_the_frame():
    df = pd.DataFrame({"symbol": ["X"]})
    cfg = C.configure_df(df, extra=C.CHART_FAMILY)
    assert set(cfg) == {"symbol", *C.CHART_FAMILY}


def test_configure_emits_streamlit_objects():
    cfg = C.configure("close", "symbol", "chart")
    assert len(cfg) == 3
    for v in cfg.values():
        assert v is not None


def test_the_sweep_aliases_resolve_to_their_ids():
    """Spellings found across the dashboard in the 2026-09-10 sweep."""
    assert C.resolve("% Chg") == "chg_pct"
    assert C.resolve("Price") == "close"
    assert C.resolve("LTP ₹") == "close"
    assert C.resolve("Gap %") == "gap_pct"
    assert C.resolve("Price %") == "price_pct_fut"
    assert C.resolve("OI %") == "oi_pct"
    assert C.resolve("RVol") == "rvol_fut"


def test_futures_rvol_is_not_the_equity_one():
    """A third volume base. Mapping it to either equity id would silently
    redefine the number a reader is looking at."""
    assert C.resolve("RVol") != "rvol"
    assert "FUTURES" in C.COLUMNS["rvol_fut"].help
    assert "20-day mean" in C.COLUMNS["rvol_fut"].help   # says what it is NOT


def test_the_declined_spellings_stay_unaliased():
    """Raw-rupee turnover is 1e7 from turnover_cr; the rest are singletons.
    This test exists so a later sweep does not 'finish the job'."""
    for name in C.NOT_ALIASED:
        assert C.resolve(name) is None, f"{name!r} should not be aliased"
