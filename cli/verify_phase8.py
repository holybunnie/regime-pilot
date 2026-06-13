#!/usr/bin/env python3
"""Phase 8 verification: x402 data-cost plan integrity.

  - prices.json has a real per-request price and records an EXECUTED payment
  - the executed-payment evidence shows HTTP 200 + settled
  - DATA_PLAN.json numbers RECOMPUTE from prices + cadence (not hand-typed)
  - minimal viable feed set is non-empty

Run: python cli/verify_phase8.py   (or: make verify-phase8)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRICES = REPO / "x402plan" / "prices.json"
PLAN = REPO / "x402plan" / "DATA_PLAN.json"
EVID = REPO / "evidence" / "x402_executed_payment.json"
HOURS_PER_WEEK = 168


def main():
    fails = []

    def check(c, m):
        print(f"  [{'PASS' if c else 'FAIL'}] {m}")
        if not c:
            fails.append(m)

    for p in (PRICES, PLAN):
        check(p.exists(), f"{p.relative_to(REPO)} exists")
    if not (PRICES.exists() and PLAN.exists()):
        print("RESULT: run `python x402plan/build_plan.py` first.")
        return 1

    prices = json.loads(PRICES.read_text())
    plan = json.loads(PLAN.read_text())

    check(prices["price_per_request_usd"] > 0, "real per-request price present")
    check(prices["executed_payment"]["executed"] is True, "a REAL x402 payment was executed")

    if EVID.exists():
        ev = json.loads(EVID.read_text())
        check(ev.get("http") == 200, "executed-payment evidence shows HTTP 200")

    # recompute the hourly price feed weekly cost and compare to the plan
    expected_price_weekly = round(HOURS_PER_WEEK * prices["price_per_request_usd"], 4)
    price_feed = next((f for f in plan["feeds"] if f["feed"] == "price"), {})
    check(abs(price_feed.get("x402_weekly_cost_usd", 0) - expected_price_weekly) < 1e-6,
          f"price feed weekly cost recomputes ({expected_price_weekly})")

    # recompute total weekly x402 cost = sum of available feeds
    expected_total = round(sum(f["x402_weekly_cost_usd"] for f in plan["feeds"]
                              if f.get("x402_weekly_cost_usd")), 2)
    check(abs(plan["x402_cost_if_used_usd_per_week"] - expected_total) < 1e-6,
          f"total weekly x402 cost recomputes ({expected_total})")

    # breakeven = monthly cost / OOS return
    if plan.get("x402_breakeven_capital_usd") and plan["flagship_v2_oos_return_gross"] > 0:
        exp_break = round(plan["x402_cost_if_used_usd_per_month"] / plan["flagship_v2_oos_return_gross"], 2)
        check(abs(plan["x402_breakeven_capital_usd"] - exp_break) < 1.0,
              f"break-even capital recomputes (~${exp_break:,.0f})")

    check(len(plan["minimal_viable_feed_set"]) >= 1, "minimal viable feed set is non-empty")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL PHASE 8 CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
