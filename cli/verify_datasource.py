#!/usr/bin/env python3
"""Item 11: the CMC Pro data-source abstraction is wired and selects correctly.

Confirms (with MOCKED env — no real key needed):
  - with no key set, the default source is the current free source (binance)
  - with a CMC Pro key present, the source switches to cmc_pro
  - an explicit override is honored
  - engine logic is untouched: the abstraction is opt-in (default == binance)

Run: python cli/verify_datasource.py   (or: make verify-datasource)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import datasource as ds  # noqa: E402


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    check(ds.select_price_source({}) == "binance",
          "default (no key) -> binance (current free source)")
    check(ds.select_price_source({"CMC_PRO_API_KEY": "mock-key-123"}) == "cmc_pro",
          "CMC Pro key present (mocked) -> cmc_pro")
    check(ds.select_price_source({"REGIME_PILOT_PRICE_SOURCE": "cmc_pro"}) == "cmc_pro",
          "explicit override -> cmc_pro")
    check(ds.select_price_source({"CMC_PRO_API_KEY": "k",
                                  "REGIME_PILOT_PRICE_SOURCE": "binance"}) == "binance",
          "explicit override beats key presence")
    check(ds.cmc_pro_available({}) is False and ds.cmc_pro_available({"CMC_PRO_API_KEY": "k"}),
          "cmc_pro_available reflects key presence")

    print()
    if fails:
        print(f"FAIL: {len(fails)} datasource check(s) failed")
        return 1
    print("ALL DATASOURCE CHECKS PASS — default binance; CMC Pro selectable when keyed (optional)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
