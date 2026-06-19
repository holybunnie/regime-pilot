#!/usr/bin/env python3
"""Unit tests for the drawdown-budget sizing law and de-risk ladder boundaries.

Run: python tests/test_sizing.py   (exit 0 = pass)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine.sizing import (Rung, remaining_drawdown_budget, position_size,  # noqa: E402
                           gross_multiplier)

LADDER = [
    Rung(0.50, 0.5),
    Rung(0.75, 0.0, except_regimes=("capitulation",)),
    Rung(0.90, 0.0),
]


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    # remaining budget
    check(approx(remaining_drawdown_budget(0.0, 0.20), 1.0), "no drawdown -> full budget")
    check(approx(remaining_drawdown_budget(0.10, 0.20), 0.5), "half budget used -> 0.5 remaining")
    check(approx(remaining_drawdown_budget(0.30, 0.20), 0.0), "over-budget -> floored at 0")

    # position size: vol-target cap binds when budget term is larger
    s = position_size(asset_vol=0.5, k=1.0, vol_target_annual=0.20,
                      current_drawdown=0.0, max_drawdown_budget=0.20, max_position_weight=1.0)
    check(approx(s, 0.4), "vol-target cap binds: 0.20/0.5 = 0.4")

    # position size: budget term binds when drawdown is deep
    s2 = position_size(asset_vol=0.5, k=0.1, vol_target_annual=0.20,
                       current_drawdown=0.10, max_drawdown_budget=0.20, max_position_weight=1.0)
    # budget term = 0.1 * 0.5 / 0.5 = 0.1 ; vol-target = 0.4 -> min = 0.1
    check(approx(s2, 0.1), "budget term binds when drawdown deep")

    # max_position_weight clamps
    s3 = position_size(asset_vol=0.1, k=1.0, vol_target_annual=0.20,
                       current_drawdown=0.0, max_drawdown_budget=0.20, max_position_weight=0.3)
    check(approx(s3, 0.3), "max_position_weight clamps oversized positions")

    # zero / negative vol -> zero size (no divide-by-zero)
    check(position_size(0.0, 1.0, 0.2, 0.0, 0.2, 1.0) == 0.0, "zero asset_vol -> zero size")

    # ---- de-risk ladder boundary tests ----
    # consumed = drawdown / budget
    check(approx(gross_multiplier(0.05, 0.20, LADDER, "chop"), 1.0),
          "25% consumed -> full exposure (below first rung)")
    check(approx(gross_multiplier(0.10, 0.20, LADDER, "chop"), 0.5),
          "exactly 50% consumed -> halve exposure")
    check(approx(gross_multiplier(0.149, 0.20, LADDER, "chop"), 0.5),
          "between 50% and 75% -> still halved")
    check(approx(gross_multiplier(0.15, 0.20, LADDER, "chop"), 0.0),
          "exactly 75% consumed -> flat")
    check(approx(gross_multiplier(0.15, 0.20, LADDER, "capitulation"), 0.5),
          "75% consumed but capitulation exempt from the 75% rung -> still 0.5")
    check(approx(gross_multiplier(0.18, 0.20, LADDER, "capitulation"), 0.0),
          "90% consumed -> flat even for capitulation (90% rung has no exemption)")

    print()
    if fails:
        print(f"FAIL: {len(fails)} sizing test(s) failed")
        return 1
    print("ALL SIZING TESTS PASS")
    return 0


def test_sizing_contract():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
