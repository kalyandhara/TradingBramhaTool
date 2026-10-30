"""paginated_df must accept a pandas Styler (deals / insider tables passed one
and crashed on len(Styler))."""
from contextlib import nullcontext

import pandas as pd
import pytest

import ui_tables as uit


@pytest.fixture
def shown(monkeypatch):
    out = []
    st = uit.st
    monkeypatch.setattr(st, "dataframe", lambda obj, **kw: out.append(obj))
    monkeypatch.setattr(st, "columns", lambda spec: [nullcontext()] * len(spec))
    monkeypatch.setattr(st, "button", lambda *a, **k: False)
    monkeypatch.setattr(st, "number_input", lambda *a, **k: a[3])
    monkeypatch.setattr(st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(st, "session_state", {})
    return out


def _red(row):
    return ["background-color: red" if row["side"] == "S" else ""] * len(row)


def _styler(n):
    df = pd.DataFrame({"side": ["B", "S"] * (n // 2), "qty": range(n)})
    return df.style.apply(_red, axis=1)


def test_styler_over_one_page_is_sliced_and_keeps_its_styles(shown):
    uit.paginated_df(_styler(60), key="t", page_size=25)
    page = shown[0]
    assert len(page.data) == 25 and list(page.data["qty"])[:2] == [0, 1]
    html = page.to_html()
    assert "background-color: red" in html


def test_styler_within_one_page_renders_whole(shown):
    uit.paginated_df(_styler(10), key="t2", page_size=25)
    assert len(shown[0].data) == 10


def test_plain_frame_still_pages(shown):
    uit.paginated_df(pd.DataFrame({"a": range(60)}), key="t3", page_size=25,
                     tint=False)
    assert len(shown[0]) == 25
