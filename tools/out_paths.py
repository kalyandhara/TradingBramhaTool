"""Where generated files go, and where to look for the ones already written — B-88.

The repo root held **30 `.xlsx`, 19 sector-rotation renders and 5 `.csv`**, all
gitignored and all generated. They broke nothing; they buried the docs, which are
the only things at the root a person is meant to read.

── Why this is not a one-line move ─────────────────────────────────────────────

The dashboard **reads these back**: `BASE_DIR.glob("sector_rotation_*.xlsx")`,
`glob("screener_export_*.csv")`, `glob("sector_rotation_orbit_*.html")`, plus
direct `screener_<today>.xlsx` lookups. Changing only the writers would leave a
year of existing exports invisible to the surface that lists them — a tidy-up that
silently deletes history from the reader's point of view is worse than the mess.

So: **new files are written to `output/`, and readers search `output/` AND the
root.** Nothing is moved and nothing is deleted. The root stops growing, existing
files keep working exactly where they are, and the clutter drains on its own as
old dated files stop being the newest.

`latest()` sorts by name across both locations, which is correct here because
every one of these filenames carries a `YYYYMMDD` stamp — the convention that made
the pile legible is the same one that makes the merge safe.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

#: Where anything generated goes from now on. Overridable so a test never writes
#: into the real tree.
OUT_DIR = Path(os.environ.get("TB_OUT_DIR") or (BASE_DIR / "output"))

#: Searched for files written before B-88. Read-only by intent: nothing new is
#: ever written here again.
LEGACY_DIR = BASE_DIR


def out_path(name: str) -> Path:
    """Absolute path for a generated file, creating `output/` on first use."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR / name


def find(pattern: str) -> list[Path]:
    """Every match for `pattern` in `output/` and the legacy root, newest first.

    Newest-first by FILENAME, not mtime: these all carry a date stamp, and a file
    copied or restored later would sort wrongly by mtime while its name still says
    exactly which session produced it.
    """
    seen: dict[str, Path] = {}
    for d in (LEGACY_DIR, OUT_DIR):        # OUT_DIR second so it wins a tie
        if not d.is_dir():
            continue
        for p in d.glob(pattern):
            if p.is_file():
                seen[p.name] = p
    return [seen[k] for k in sorted(seen, reverse=True)]


def latest(pattern: str) -> Path | None:
    """The newest match across both locations, or None."""
    hits = find(pattern)
    return hits[0] if hits else None


def resolve(name: str) -> Path | None:
    """An exact filename in either location, preferring `output/`."""
    for d in (OUT_DIR, LEGACY_DIR):
        p = d / name
        if p.is_file():
            return p
    return None
