"""Tests for event_study.py (policy event-study engine), offline.

The engine is a measuring instrument, so the tests are about it measuring the
right thing and nothing else:

  * events are validated, not trusted — an unknown label or a duplicate date is
    an error, never a silently different sample;
  * a planted effect must be found and an unplanted control must not;
  * the null must be reproducible from its seed and must never draw a day that
    sits next to a real event.
"""
import textwrap

import numpy as np
import pandas as pd
import pytest

import event_study as es


HEADER = "date,event_type,label,scheduled,time_ist,source_url,notes\n"


def _csv(tmp_path, body):
    p = tmp_path / "events.csv"
    p.write_text(HEADER + textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return p


# ── events ────────────────────────────────────────────────────────────────────

def test_load_events_filters_and_sorts(tmp_path):
    p = _csv(tmp_path, """
        2020-02-06,mpc,hold,1,11:45,u,
        2020-02-01,budget,full,1,11:00,u,
        2019-12-05,mpc,hold,1,11:45,u,
    """)
    ev = es.load_events(p, types=["mpc"])
    assert list(ev["event_type"]) == ["mpc", "mpc"]
    assert list(ev["date"]) == [pd.Timestamp("2019-12-05"), pd.Timestamp("2020-02-06")]


def test_load_events_drops_unscheduled_by_default(tmp_path):
    p = _csv(tmp_path, """
        2020-03-27,mpc,cut,0,10:00,u,off-cycle
        2020-02-06,mpc,hold,1,11:45,u,
    """)
    assert len(es.load_events(p)) == 1
    allev = es.load_events(p, scheduled_only=False)
    assert len(allev) == 2
    assert allev["scheduled"].tolist() == [1, 0]


def test_load_events_rejects_unknown_label(tmp_path):
    p = _csv(tmp_path, "2020-02-06,mpc,pause,1,11:45,u,\n")
    with pytest.raises(ValueError, match="pause"):
        es.load_events(p)


def test_load_events_rejects_duplicate(tmp_path):
    p = _csv(tmp_path, """
        2020-02-06,mpc,hold,1,11:45,u,
        2020-02-06,mpc,cut,1,11:45,u,
    """)
    with pytest.raises(ValueError, match="duplicate"):
        es.load_events(p)
