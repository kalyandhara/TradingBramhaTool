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


# ── UI-2 · tone, tint and pinning ────────────────────────────────────────────

def test_tone_is_part_of_the_definition_not_an_override():
    """The whole point of putting tone in the registry: a quantity that means
    'up is good' on one page and nothing on another is the drift this module
    exists to end. So tone must NOT be in MUTABLE."""
    assert "tone" not in C.MUTABLE
    assert "pinned" not in C.MUTABLE
    with pytest.raises(ValueError):
        C.configure("chg_pct", overrides={"chg_pct": {"tone": "heat"}})


def test_directional_columns_carry_a_tone():
    """These are the columns whose sign IS the reading. An untoned one renders
    as a grey number in a wall of grey numbers."""
    for cid in ("chg_pct", "gap_pct", "bo_gain_pct", "from_52w_high_pct"):
        assert C.COLUMNS[cid].tone == "signed", cid
    assert C.COLUMNS["rvol"].tone == "heat"
    assert C.COLUMNS["rs_rank"].tone == "rank"


def test_tint_returns_a_styler_only_when_something_is_toned():
    """An untoned table must pay nothing — and must stay a DataFrame so the
    caller can hand either result to st.dataframe unchanged."""
    import pandas as pd
    toned = pd.DataFrame({"symbol": ["A"], "chg_pct": [1.5]})
    assert hasattr(C.tint(toned), "to_html")          # Styler
    plain = pd.DataFrame({"whatever": [1]})
    assert C.tint(plain) is plain                     # untouched frame


def test_signed_tint_colours_the_cell_by_sign_and_leaves_zero_alone():
    assert "background-color" in C._tint_signed(2.4)
    assert C.TINTS["pos"][0] in C._tint_signed(2.4)
    assert C.TINTS["neg"][0] in C._tint_signed(-2.4)
    assert C._tint_signed(0) == ""                    # zero is not news
    assert C._tint_signed(None) == ""
    assert C._tint_signed("n/a") == ""


def test_heat_has_a_floor_so_it_does_not_paint_every_row():
    """A heat scale with no floor tints the whole column and says nothing."""
    assert C._tint_heat(1.0) == ""
    assert C._tint_heat(C.RVOL_FLOOR - 0.01) == ""
    assert C._tint_heat(C.RVOL_FLOOR) != ""


def test_rank_tint_reads_the_LAST_rung_of_a_walk():
    """`rs_walk` arrives as '92 -> 94 -> 35 -> 36'. Tinting on the first rung
    would colour a row by where it used to be."""
    lagging = C._tint_rank("92 -> 94 -> 35 -> 12")
    leading = C._tint_rank("3 -> 4 -> 60 -> 95*")     # trailing * = guest
    assert C.TINTS["rank_lo"][0] in lagging
    assert C.TINTS["rank_hi"][0] in leading
    assert C._tint_rank("40 -> 50 -> 55 -> 50") == ""  # mid is not news


def test_identity_is_pinned_and_numbers_are_not():
    """Pinning a number pins the wrong half of the row."""
    assert C.COLUMNS["symbol"].pinned is True
    assert C.COLUMNS["chg_pct"].pinned is False


def test_notes_is_a_registry_column_with_a_tooltip():
    """It is editable and persisted, which is exactly why its definition must
    live in one place like every other column."""
    assert C.COLUMNS["notes"].help
    assert "symbol_notes" in C.COLUMNS["notes"].help


def test_no_duplicate_ids_in_the_registry_literal():
    """A dict literal silently keeps the LAST of two identical keys.

    This is not hypothetical: on 2026-09-10 a second `"notes"` entry was added to
    the identity block while one already existed further down, and Python
    resolved it to the older definition with no error anywhere. The registry
    looked correct, `COLUMNS["notes"]` returned something sensible, and the new
    tooltip simply never existed. Only a test that reads the SOURCE can see it.
    """
    import ast
    import pathlib
    src = pathlib.Path(C.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) in ("COLUMNS", "ALIASES")
                   for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        keys = [k.value for k in node.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        assert not dupes, (
            f"duplicate keys in the registry literal: {dupes}. Python keeps the "
            f"last one and reports nothing.")
