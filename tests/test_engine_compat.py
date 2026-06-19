"""Known-answer regression proving engine hardening preserves legacy strategy results."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt  # noqa: E402

BASELINE = json.loads((REPO / "evidence" / "engine_compat_baseline.json").read_text())


def synthetic_panels():
    hours = BASELINE["fixture_hours"]
    idx = pd.date_range("2025-01-01", periods=hours, freq="h", tz="UTC")
    rng = np.random.default_rng(BASELINE["numpy_seed"])
    symbols = [token["symbol"] for token in
               json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]]
    close = pd.DataFrame({
        symbol: 100 * np.exp(np.cumsum(
            rng.normal(0.00001 * (i % 3 - 1), 0.004 + 0.0001 * i, len(idx))))
        for i, symbol in enumerate(symbols)
    }, index=idx)
    dvol = pd.DataFrame({
        symbol: 1e8 * (1 + i / 10) * (1 + 0.05 * np.sin(np.arange(len(idx)) / 24))
        for i, symbol in enumerate(symbols)
    }, index=idx)
    fear_greed = pd.Series(50 + 30 * np.sin(np.arange(len(idx)) / (24 * 20)), index=idx)
    return {
        "close": close,
        "dvol24": dvol,
        "btc": close["BTC"],
        "fear_greed": fear_greed,
        "index": idx,
    }


def result_hash(result):
    digest = hashlib.sha256()
    digest.update(result["equity"].to_csv(index=False, lineterminator="\n").encode())
    digest.update(result["trades"].to_csv(index=False, lineterminator="\n").encode())
    digest.update(json.dumps(
        result["summary"], sort_keys=True, separators=(",", ":")).encode())
    return digest.hexdigest()


def test_legacy_results_unchanged():
    panels = synthetic_panels()
    for relative, expected in BASELINE["results"].items():
        spec = json.loads((REPO / relative).read_text())
        result = bt.run(spec, panels=panels, feats=bt.build_features(spec, panels))
        assert result_hash(result) == expected, relative


def main():
    test_legacy_results_unchanged()
    print("  [PASS] engine hardening preserves momentum, v1, and live v2 result hashes")
    return 0
