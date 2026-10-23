"""model_version.py — stamp each stored recommendation with the code that made it.

The recommendation audit (`rec_audit.py`) compares picks made BEFORE a weight
change with picks made AFTER it. That is only possible if every stored row says
which code and which weights produced it. Rows written before 2026-10-22 have
no stamp; the audit treats them as one "pre-versioning" cohort.

A version is `<git short sha>[+dirty]/w:<weights fingerprint>`:
  * the sha says which code ran (a "+dirty" tree means uncommitted edits ran);
  * the fingerprint changes when any weight/table passed in changes, even with
    no commit — so an edited-but-uncommitted weight is still told apart.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def git_sha(repo: Path = REPO) -> str:
    """Short HEAD sha, '+dirty' if tracked files are modified; 'nogit' on any failure."""
    try:
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if not sha:
            return "nogit"
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain",
                                "--untracked-files=no"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except Exception:
        return "nogit"


def fingerprint(*parts) -> str:
    """8-hex digest of the parts, stable across runs and dict ordering."""
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:8]


def version(*weight_parts, repo: Path = REPO) -> str:
    """'<sha>/w:<fp>' — or just '<sha>' when no weights are passed."""
    sha = git_sha(repo)
    return f"{sha}/w:{fingerprint(*weight_parts)}" if weight_parts else sha
