"""Build cache/cardinality_deep/ - the full daily history for the liquid universe.

    py -3 tools/qm_deep_cache.py        # ~460 names, ~19y, five batched requests

B-58's 2026-09-11 amendment needed more bars than `cache/cardinality/` carries (743
per name, the `--years 2` build). This writes a DEEPER cache to its own directory
and leaves the shared one untouched: `cache/cardinality/` is the panel behind B-43,
B-57 and the QM study's own DIAGNOSTIC arm, so re-cutting it in place would silently
move settled results.

Yield on 2026-09-11: 459 names, median 4,122 bars (max 4,939), 1.50M bars total
against the shallow cache's ~264k.


Reuses renko_quality_cardinality.export_bars unchanged, with CACHE repointed, so
the bar files are byte-identical in shape to the shared panel's -- only deeper.
"""
from pathlib import Path
import renko_quality_cardinality as card

DEEP = card.HERE / "cache" / "cardinality_deep"
card.CACHE = DEEP
syms, date = card.universe(500)
print(f"universe {len(syms)} names (bhavcopy {date})", flush=True)
paths = card.export_bars(syms, years=19)
print(f"cached {len(paths)} names into {DEEP.name}")
