#!/usr/bin/env python3
"""Compute the current live signal for the FROZEN flagship spec.

The attested signal is deterministic from public data available at the decision hour:
  { spec_version, spec_hash, timestamp_utc, regime, target_weights }

target_weights are the full-budget intended allocation (drawdown=0) produced by the
SAME engine function the backtest uses, so anyone can reproduce the signal from public
data and the frozen spec. The live-drawdown de-risk ladder is a PnL/execution overlay
applied when reconstructing the forward equity curve at reveal time, not part of the
point-in-time signal.
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt          # noqa: E402
from engine import sizing as sz            # noqa: E402
from attest.hashing import spec_hash, universe_hash       # noqa: E402

WEIGHT_ROUND = 6
UNIVERSE_PATH = REPO / "spec" / "universe.json"


def _extend(panels, effective_hour, benchmark="BTC"):
    """Add a row at effective_hour so shifted features have a row there. Shifted
    features at effective_hour use ONLY data strictly before it, so the (possibly
    absent/partial) effective_hour bar is never read — keeping the signal forward."""
    idx = panels["index"].union([effective_hour])
    close = panels["close"].reindex(idx)
    dvol = panels["dvol24"].reindex(idx)
    fg = panels["fear_greed"].reindex(idx).ffill()
    return {"close": close, "dvol24": dvol, "btc": close[benchmark],
            "fear_greed": fg, "index": idx}


def compute_signal(spec_path, effective_hour=None):
    """Signal effective for the hour [effective_hour, effective_hour+1h). Uses only
    data < effective_hour, so committing within that hour is a true forward prediction.
    effective_hour defaults to the current wall-clock hour boundary (UTC)."""
    spec = json.loads(Path(spec_path).read_text())
    universe = [t["symbol"] for t in json.loads(UNIVERSE_PATH.read_text())["tokens"]]
    panels = bt.load_panels(universe)
    if effective_hour is None:
        effective_hour = pd.Timestamp.now(tz="UTC").floor("h")
    t = pd.Timestamp(effective_hour)
    panels = _extend(panels, t)

    feats = bt.build_features(spec, panels)
    regimes = bt.assign_regimes(spec, feats)
    ladder = sz.ladder_from_spec(spec["risk"])
    if t not in feats.index or feats.loc[t].isna().any():
        raise RuntimeError(f"features for effective hour {t} not fully populated")

    regime = regimes.loc[t]
    row = feats.loc[t]
    w = bt.target_weights(spec, row, panels, t, regime, 0.0, ladder, universe)
    # keep non-zero weights, including NEGATIVE (short) ones for v2 long/short specs.
    # For long-only v1 all weights are >= 0, so this is identical to the old v>0 filter.
    weights = {a: round(v, WEIGHT_ROUND) for a, v in w.items() if v != 0}

    payload = {
        "spec_version": spec["meta"]["version"],
        "spec_hash": spec_hash(spec_path),
        "universe_hash": universe_hash(UNIVERSE_PATH),
        "timestamp_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": regime,
        "target_weights": weights,
    }
    return payload


if __name__ == "__main__":
    sp = sys.argv[1] if len(sys.argv) > 1 else str(REPO / "spec" / "regime_pilot.spec.json")
    print(json.dumps(compute_signal(sp), indent=2, sort_keys=True))
