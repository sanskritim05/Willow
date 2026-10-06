"""Where things live, and the cached clean panel.

The panel (one row per person per round, built by nhats.load_panel) holds respondent data. It is cached at
data/clean/panel.parquet, which is git-ignored and must stay on this machine.
"""
from __future__ import annotations

import os
import time

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_NHATS = os.path.expanduser("~/Downloads/NHATS Data/data/raw")
PANEL_CACHE = os.path.join(ROOT, "data", "clean", "panel.parquet")


def load_panel(nhats_dir: str | None = None, refresh: bool = False, log=print) -> pd.DataFrame:
    """The cleaned panel: read from the cache, or built from the NHATS files (and cached) if missing or refresh=True."""
    if os.path.exists(PANEL_CACHE) and not refresh:
        log(f"[data] cached panel {os.path.relpath(PANEL_CACHE, ROOT)} (use --refresh to rebuild)")
        return pd.read_parquet(PANEL_CACHE)
    from .nhats import load_panel as _load
    t0 = time.time()
    panel = _load(os.path.expanduser(nhats_dir or DEFAULT_NHATS))
    os.makedirs(os.path.dirname(PANEL_CACHE), exist_ok=True)
    panel.to_parquet(PANEL_CACHE, index=False)
    log(f"[data] built panel from NHATS in {time.time() - t0:.0f}s -> {os.path.relpath(PANEL_CACHE, ROOT)} (keep local)")
    return panel
