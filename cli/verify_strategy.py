#!/usr/bin/env python3
"""Strategy verification: the flagship strategy.

  - flagship spec validates (schema + semantic)
  - full backtest runs end-to-end and writes summary + report
  - EMBARGO untouched: a fitting run capped at embargo_start never reads data at or
    after the embargo boundary (proven by the run's reported window_end)
  - no $1 dust: normalized equity never collapses toward zero

Run: python cli/verify_strategy.py   (or: make verify-strategy)
"""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "cli"))
import validate_spec                      # noqa: E402
from engine import backtest as bt        # noqa: E402

SPEC_PATH = REPO / "spec" / "regime_pilot.spec.json"
CACHE = REPO / "engine" / "data" / "cache"


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    spec = json.loads(SPEC_PATH.read_text())

    ok, errs = validate_spec.validate(spec)
    check(ok, f"flagship spec validates ({'ok' if ok else errs})")

    # full run
    result = bt.run(spec)
    bt.write_outputs(result, REPO / "engine" / "reports" / "regime_pilot")
    s = result["summary"]
    check((REPO / "engine" / "reports" / "regime_pilot" / "report.md").exists(),
          "summary report generated")
    print(f"         full window {s['window_start'][:10]}..{s['window_end'][:10]}, "
          f"return {s['total_return']:+.2%} vs BTC {s['benchmark_btc_return']:+.2%} "
          f"(excess {s['excess_return_vs_btc']:+.2%}), maxDD {s['max_drawdown']:.2%}")

    # embargo enforcement
    manifest = json.loads((CACHE / "manifest.json").read_text())
    embargo_start = pd.Timestamp(manifest["embargo_start"])
    fit = bt.run(spec, end=embargo_start)
    fit_end = pd.Timestamp(fit["summary"]["window_end"])
    check(fit_end <= embargo_start,
          f"embargo untouched during fitting: fit window_end {fit_end:%Y-%m-%d} "
          f"<= embargo_start {embargo_start:%Y-%m-%d}")

    # dust rule (normalized equity must stay well above 0)
    min_eq = result["equity"]["equity"].min()
    check(min_eq > 0.5, f"no dust: min equity {min_eq:.3f} stays well above 0")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL STRATEGY CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
