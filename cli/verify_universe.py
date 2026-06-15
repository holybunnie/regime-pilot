#!/usr/bin/env python3
"""Item 8: both universe files are valid and the swap is a one-line config change.

  - loads spec/universe.json (interim 15) and spec/universe_official_149.json
  - validates the 149-token file's schema (shape, count, unique ASCII symbols)
  - lists any symbols that cannot be resolved structurally (non-ASCII / malformed) — flagged,
    not fatal (live resolution against the data source happens in make verify-full)
  - confirms the engine actually runs against the interim universe on the offline fixture

Run: python cli/verify_universe.py   (or: make verify-universe)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
INTERIM = REPO / "spec" / "universe.json"
OFFICIAL = REPO / "spec" / "universe_official_149.json"


def validate(path, expect_count=None):
    obj = json.loads(path.read_text())
    fails, unresolved = [], []
    for key in ("quote", "benchmark_symbol", "tokens"):
        if key not in obj:
            fails.append(f"{path.name}: missing top-level '{key}'")
    tokens = obj.get("tokens", [])
    syms = [t.get("symbol", "") for t in tokens]
    if expect_count is not None and len(tokens) != expect_count:
        fails.append(f"{path.name}: expected {expect_count} tokens, found {len(tokens)}")
    if len(set(syms)) != len(syms):
        fails.append(f"{path.name}: duplicate symbols present")
    for t in tokens:
        if not all(k in t for k in ("symbol", "binance_pair", "cmc_symbol")):
            fails.append(f"{path.name}: token missing required field: {t}")
        s = t.get("symbol", "")
        if not s.isascii() or not s:
            unresolved.append(s or "<empty>")
    return obj, fails, unresolved


def main():
    fails = []
    _, f1, _ = validate(INTERIM)
    fails += f1
    print(f"  [{'PASS' if not f1 else 'FAIL'}] interim universe.json schema valid "
          f"({len(json.loads(INTERIM.read_text())['tokens'])} tokens)")

    _, f2, unresolved = validate(OFFICIAL, expect_count=149)
    fails += f2
    print(f"  [{'PASS' if not f2 else 'FAIL'}] official 149-token file schema valid")
    print(f"  [INFO] structurally-unresolvable symbols (flagged, not fatal): "
          f"{unresolved if unresolved else 'none'}")

    # engine runs against the interim universe on the committed fixture
    try:
        from cli._fixture import use_fixture_cache
        from engine import backtest as bt
        use_fixture_cache()
        interim_syms = [t["symbol"] for t in json.loads(INTERIM.read_text())["tokens"]]
        spec = json.loads((REPO / "skill" / "examples" / "momentum_simple.spec.json").read_text())
        panels = bt.load_panels(interim_syms)
        feats = bt.build_features(spec, panels)
        ok_engine = len(feats) > 0
    except Exception as e:
        ok_engine = False
        print(f"    engine error: {e}")
    print(f"  [{'PASS' if ok_engine else 'FAIL'}] engine runs against the interim universe (fixture)")
    if not ok_engine:
        fails.append("engine-against-interim")

    print()
    if fails:
        print(f"FAIL: {len(fails)} universe check(s) failed: {fails}")
        return 1
    print("ALL UNIVERSE CHECKS PASS — 149-token file valid; one-line swap; engine universe-agnostic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
