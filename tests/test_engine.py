#!/usr/bin/env python3
"""Verification: determinism + no-lookahead guard + feature shift.

Run: python tests/test_engine.py   (exit 0 = pass)
"""
import hashlib
import copy
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt          # noqa: E402
from engine import indicators as ind       # noqa: E402

SPEC = json.loads((REPO / "skill" / "examples" / "momentum_simple.spec.json").read_text())


def _hash_dir(d):
    h = hashlib.sha256()
    for f in sorted(Path(d).iterdir()):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def check_determinism():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        bt.write_outputs(bt.run(SPEC), a)
        bt.write_outputs(bt.run(SPEC), b)
        ha, hb = _hash_dir(a), _hash_dir(b)
        ok = ha == hb
        print(f"  [{'PASS' if ok else 'FAIL'}] determinism: two runs byte-identical ({ha[:12]})")
        return ok


def check_lookahead_guard():
    close = pd.DataFrame(
        {"BTC": [1.0, 2.0, 3.0, 4.0]},
        index=pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC"))
    acc = bt.GuardedAccessor(close)
    T = close.index[2]                 # decision at the 3rd hour
    # reading the future must raise
    try:
        acc.raw_at("BTC", close.index[3], T)
        print("  [FAIL] lookahead: future read was NOT rejected")
        return False
    except bt.LookaheadError:
        pass
    # reading at exactly T must also raise (T is not strictly before T)
    try:
        acc.raw_at("BTC", T, T)
        print("  [FAIL] lookahead: read at exactly T was NOT rejected")
        return False
    except bt.LookaheadError:
        pass
    # reading the past is allowed and correct
    val = acc.decision_price("BTC", T)
    ok = val == 2.0
    print(f"  [{'PASS' if ok else 'FAIL'}] no-lookahead guard: future/at-T rejected, past read = {val}")
    return ok


def check_feature_shift():
    """A feature at hour T must equal the raw indicator computed through T-1."""
    panels = bt.load_panels([t["symbol"] for t in
                             json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]])
    feats = bt.build_features(SPEC, panels)
    raw_sma = ind.sma(panels["btc"], 168)        # unshifted
    # pick a row with data
    idx = feats["btc_sma_7d"].dropna().index[100]
    prev_idx = panels["index"][panels["index"].get_loc(idx) - 1]
    ok = np.isclose(feats["btc_sma_7d"].loc[idx], raw_sma.loc[prev_idx])
    print(f"  [{'PASS' if ok else 'FAIL'}] feature shift: feature[T] uses data through T-1")
    return ok


def check_universe_resolution():
    spec = copy.deepcopy(SPEC)
    spec["universe"] = {
        "source": "explicit",
        "symbols": ["BTC", "ETH", "BNB"],
        "exclude_symbols": ["ETH"],
    }
    got = bt.resolve_universe(spec, ["BTC", "ETH", "BNB", "SOL"])
    ok = got == ["BTC", "BNB"]
    print(f"  [{'PASS' if ok else 'FAIL'}] universe contract: explicit allow/exclude -> {got}")
    return ok


def check_gross_cap():
    spec = copy.deepcopy(SPEC)
    spec["risk"]["max_gross_exposure"] = 0.5
    spec["risk"]["per_asset_cap"] = 0.4
    spec["playbooks"]["risk_on"] = {
        "action": "staged_reentry",
        "assets": ["BTC", "ETH", "BNB"],
        "reentry_feature": "fg_level",
    }
    panels = bt.load_panels(["BTC", "ETH", "BNB"])
    t = panels["index"][-1]
    row = pd.Series({"btc_vol": 0.5, "fg_level": 100.0})
    weights = bt.target_weights(spec, row, panels, t, "risk_on", 0.0, [], ["BTC", "ETH", "BNB"])
    gross = sum(abs(v) for v in weights.values())
    ok = gross <= 0.5 + 1e-12
    print(f"  [{'PASS' if ok else 'FAIL'}] staged reentry respects max gross ({gross:.3f})")
    return ok


def main():
    results = [check_lookahead_guard(), check_feature_shift(), check_universe_resolution(),
               check_gross_cap(), check_determinism()]
    print()
    if all(results):
        print("ALL ENGINE TESTS PASS")
        return 0
    print("FAIL: one or more engine tests failed")
    return 1


def test_lookahead_guard():
    assert check_lookahead_guard()


def test_feature_shift():
    assert check_feature_shift()


def test_determinism():
    assert check_determinism()


def test_universe_resolution():
    assert check_universe_resolution()


def test_gross_cap():
    assert check_gross_cap()


if __name__ == "__main__":
    sys.exit(main())
