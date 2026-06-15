#!/usr/bin/env python3
"""Generate the committed SYNTHETIC fixture dataset used by the OFFLINE `make verify`.

These are NOT market data and NOT a result — they are deterministic, seeded, made-up
series whose only job is to let the engine's determinism / no-lookahead / falsification
checks run on a fresh clone with no network and no downloaded data. The values are stored
as plain CSV (text, diffable, not gitignored); the offline verifier converts them to the
parquet cache layout the engine expects, in a throwaway temp dir, at run time.

Run: python cli/build_fixtures.py   (regenerates tests/fixtures/cache_csv/*.csv)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
OUT = REPO / "tests" / "fixtures" / "cache_csv"
HOURS = 720                      # 30 days hourly — enough for 168h windows + headroom
START = "2025-01-01T00:00:00Z"
WATERMARK = "SYNTHETIC FIXTURE — NOT A RESULT"


def symbols():
    import json
    return [t["symbol"] for t in json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    idx = pd.date_range(START, periods=HOURS, freq="h", tz="UTC")
    for i, s in enumerate(symbols()):
        rng = np.random.default_rng(1000 + i)            # deterministic per symbol
        # gentle random walk so SMAs/vols are well-defined and non-degenerate
        steps = rng.normal(0, 0.01, size=HOURS)
        close = 100.0 * np.exp(np.cumsum(steps))
        volume = rng.uniform(1e6, 5e6, size=HOURS)
        df = pd.DataFrame({"close": close, "volume": volume}, index=idx)
        df.index.name = "timestamp"
        df.to_csv(OUT / f"ohlcv_{s}.csv")
    rng = np.random.default_rng(42)
    fg = pd.DataFrame({"fear_greed": rng.integers(10, 90, size=HOURS)}, index=idx)
    fg.index.name = "timestamp"
    fg.to_csv(OUT / "fear_greed.csv")
    (OUT / "MANIFEST.txt").write_text(
        f"{WATERMARK}\n{len(symbols())} symbols x {HOURS} hourly rows + fear_greed, "
        f"seeded (deterministic). Regenerate: python cli/build_fixtures.py\n")
    print(f"wrote {len(symbols())+1} fixture CSVs to {OUT}  ({WATERMARK})")


if __name__ == "__main__":
    build()
