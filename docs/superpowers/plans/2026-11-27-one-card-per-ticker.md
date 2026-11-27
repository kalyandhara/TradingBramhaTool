# One Card per Ticker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recommendation Audit's card views show one card per ticker at its latest pick date, listing every scanner; the pop-up's chart titles name the ticker.

**Architecture:** One pure helper, `rec_audit_replay.group_by_ticker`, applied after filtering/sorting in the three views (Post-mortems queue + counts, Pick replay picker, All picks). Statistics untouched.

**Tech Stack:** Python, pandas, Streamlit, Plotly, pytest.

**Spec:** `docs/superpowers/specs/2026-11-27-one-card-per-ticker-design.md`

## Global Constraints

- Statistics (tiles, cohorts, slices, lessons, proposals, track record) keep every pick.
- No storage change.
- Cause-button counts must equal the cards shown under them.

## Review Focus

1. Grouping before the cause filter: a ticker whose latest failure is EVENT_GAP but an older one CHASED appears only under EVENT_GAP (counts match cards). (Task 1)
2. Same symbol, same date, several scanners → one card, all scanner names, no duplicates. (Task 1)
3. Opportunity source (no `scanner` column) groups by symbol without error. (Task 1)
4. Empty frame passes through. (Task 1)

---

### Task 1: `group_by_ticker` and the three views

**Files:**
- Modify: `tools/rec_audit_replay.py` (`group_by_ticker`; `replay_candidates` groups before the tag filter; `replay_figure` titles carry the symbol)
- Modify: `tools/desk_pages/rec_audit_page.py` (`review_queue` groups before the tag filter; `_card` header; `_all_picks` grouped)
- Test: `tools/test_rec_audit_replay.py`, `tools/test_rec_audit_page.py`

**Interfaces:**
- Produces: `rp.group_by_ticker(eps: pd.DataFrame) -> pd.DataFrame` — one row per `symbol`: the first row (incoming order) among that symbol's latest `rec_date`; adds `scanners_all` (", "-joined unique `scanner` values on that date, in order; "" without a `scanner` column), `earlier_dates` (", "-joined other `rec_date`s, newest first) and `n_picks` (rows grouped). Keeps the incoming order of the kept rows and the index.

- [ ] **Step 1: Failing tests**

```python
def test_group_by_ticker_keeps_latest_and_lists_scanners():
    eps = pd.DataFrame({"episode_id": list("abcde"), "symbol": ["M", "M", "M", "X", "M"],
                        "scanner": ["Base", "VCP", "Base", "S", "Old"],
                        "rec_date": ["2026-10-13", "2026-10-13", "2026-10-13", "2026-10-13",
                                     "2026-08-14"]})
    g = rp.group_by_ticker(eps)
    m = g.set_index("symbol").loc["M"]
    assert list(g["symbol"]) == ["M", "X"] and m["episode_id"] == "a"
    assert m["scanners_all"] == "Base, VCP" and m["earlier_dates"] == "2026-08-14"
    assert m["n_picks"] == 4

def test_group_by_ticker_without_scanner_column_and_empty():
    eps = pd.DataFrame({"episode_id": ["a", "b"], "symbol": ["M", "M"],
                        "rec_date": ["2026-10-13", "2026-11-02"]})
    g = rp.group_by_ticker(eps)
    assert list(g["episode_id"]) == ["b"] and g["scanners_all"].iloc[0] == ""
    assert rp.group_by_ticker(eps.iloc[0:0]).empty

def test_review_queue_counts_match_cards():   # test_rec_audit_page.py
    # M: latest failure EVENT_GAP (2026-10-13), older CHASED (2026-08-14)
    q_all = page.review_queue(eps); counts = page.tag_counts(eps)
    assert list(q_all["symbol"]).count("M") == 1
    assert counts.get("CHASED", 0) == 0 and page.review_queue(eps, "CHASED").empty

def test_replay_titles_name_the_ticker():
    fig = rp.replay_figure(_frame(), _ep(symbol="TEST"))
    titles = [a.text for a in fig.layout.annotations]
    assert "TEST · Pick day · 2026-08-14" in titles
```

- [ ] **Step 2:** `py -3 -m pytest test_rec_audit_replay.py test_rec_audit_page.py -q -p no:cacheprovider` → the new tests FAIL.
- [ ] **Step 3:** Implement `group_by_ticker`; call it in `review_queue` (after failure filter + sort, before the tag filter), in `replay_candidates` (after sort, before the tag filter) and in `_all_picks`. `_card` header: `**SYM** · picked D · N scanners: …` when `scanners_all` has more than one name, else today's `· scanner`; caption `Also picked: …` when `earlier_dates`. `replay_figure` titles: `f"{sym} · Pick day · {rec}"`, `f"{sym} · Since then · to …"`.
- [ ] **Step 4:** Same command → PASS; then the full suite → no new failures.
- [ ] **Step 5:** Commit (`feat(rec-audit): one card per ticker at its latest pick`).

### Task 2: Verify on a fresh :8502

- [ ] Post-mortems on "Raw scanner hits": MOTISONS appears once with its scanners listed; the cause counts equal the cards; the Replay pop-up titles name the ticker. Screenshot.
