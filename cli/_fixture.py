#!/usr/bin/env python3
"""Materialise the synthetic CSV fixtures into the parquet cache layout the engine reads,
in a temp dir, and point the (frozen) engine at it AT RUN TIME only.

This never writes into engine/data/cache and never edits engine/backtest.py — it only sets
the module-level CACHE attribute inside this Python process. The live committer runs in its
own process and is completely unaffected.
"""
import atexit
import shutil
import tempfile
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV_DIR = REPO / "tests" / "fixtures" / "cache_csv"
WATERMARK = "SYNTHETIC FIXTURE — NOT A RESULT"


def use_fixture_cache():
    """Build parquet cache from the committed CSV fixtures and route the engine to it.
    Returns the temp cache dir. Raises if fixtures are missing."""
    if not CSV_DIR.exists():
        raise SystemExit(f"FATAL: fixtures missing at {CSV_DIR} — run python cli/build_fixtures.py")
    tmp = Path(tempfile.mkdtemp(prefix="rp_fixture_cache_"))
    atexit.register(lambda: shutil.rmtree(tmp, ignore_errors=True))
    for csv in CSV_DIR.glob("*.csv"):
        df = pd.read_csv(csv, index_col=0, parse_dates=True)
        df.to_parquet(tmp / (csv.stem + ".parquet"))
    from engine import backtest as bt
    bt.CACHE = tmp                      # runtime-only redirect (this process only)
    return tmp
