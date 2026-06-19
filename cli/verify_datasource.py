#!/usr/bin/env python3
"""Verify CMC Pro source selection, identifiers, and normalization.

Confirms (with MOCKED env — no real key needed):
  - with no override, the frozen v2 source remains binance
  - a Pro-capable CMC_API_KEY makes the adapter available without silently switching
  - an explicit override is required for the versioned cmc_pro cutover

Run: python cli/verify_datasource.py   (or: make verify-datasource)
"""
import sys
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import datasource as ds  # noqa: E402
from engine.data import cmc_pro       # noqa: E402


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    check(ds.select_price_source({}) == "binance",
          "default (no key) -> binance (frozen v2 source)")
    check(ds.select_price_source({"CMC_API_KEY": "mock-key-123"}) == "binance",
          "CMC key presence alone does not alter frozen v2")
    check(ds.select_price_source({"CMC_API_KEY": "mock-key-123",
                                  "REGIME_PILOT_PRICE_SOURCE": "cmc_pro"}) == "cmc_pro",
          "explicit override -> cmc_pro")
    check(ds.select_price_source({"CMC_PRO_API_KEY": "k",
                                  "REGIME_PILOT_PRICE_SOURCE": "binance"}) == "binance",
          "explicit override beats key presence")
    check(ds.cmc_pro_available({}) is False and ds.cmc_pro_available({"CMC_API_KEY": "k"}),
          "cmc_pro_available reflects CMC_API_KEY presence")
    ids = json.loads(cmc_pro.CMC_IDS.read_text())
    universe = json.loads(cmc_pro.UNIVERSE.read_text())
    symbols = {token["symbol"] for token in universe["tokens"]}
    check(symbols == set(ids), "every active symbol has one stable CMC numeric id")
    check(len(ids.values()) == len(set(ids.values())), "CMC numeric ids are unique")

    sample = {
        "status": {"error_code": 0},
        "data": {"id": 1, "quotes": [{
            "time_open": "2026-06-18T12:00:00Z",
            "quote": {"USD": {"open": 1, "high": 2, "low": 0.5, "close": 1.5,
                              "volume": 1000, "timestamp": "2026-06-18T12:59:59Z"}},
        }]},
    }
    frame = cmc_pro.normalize_ohlcv(sample, 1)
    check(not frame.empty and frame.iloc[0]["volume_24h_usd"] == 1000,
          "CMC response normalizes OHLCV and preserves quote volume semantics")

    print()
    if fails:
        print(f"FAIL: {len(fails)} datasource check(s) failed")
        return 1
    print("ALL DATASOURCE CHECKS PASS — CMC Pro ready; cutover remains explicit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
