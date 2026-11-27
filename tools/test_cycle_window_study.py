"""Hand-checked cases for the B-204 scorer's hit and baseline."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cycle_window_study import score_event  # noqa: E402


def test_hit_and_exact_sliding_baseline():
    # t=100, window 105..109 (w=5); span S = 101..110 (last 90 + 2*10) -> 6 placements.
    # One low at 107: placements starting 103,104,105,106 contain it -> 4/6.
    hit, base = score_event(100, 105, 109, 90, 10, np.array([50, 107]), 500)
    assert hit == 1
    assert base == pytest.approx(4 / 6)


def test_miss_window_clipped_to_future_and_lows_outside_span_ignored():
    # from 98 is clipped to 101 -> window 101..103 (w=3); low at 200 is outside S.
    hit, base = score_event(100, 98, 103, 90, 10, np.array([200]), 500)
    assert (hit, base) == (0, 0.0)


def test_skips_when_unsettled_or_span_too_short():
    assert score_event(100, 105, 109, 90, 10, np.array([107]), 130) is None   # 109+30 >= 130
    assert score_event(100, 105, 120, 90, 5, np.array([107]), 500) is None    # S 101..100 too short
    assert score_event(100, 95, 100, 80, 10, np.array([]), 500) is None       # window all in the past
