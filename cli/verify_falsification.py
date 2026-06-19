#!/usr/bin/env python3
"""Falsification verification: falsification report completeness + integrity.

  - deflated-Sharpe known-answer tests pass
  - REPORT.md and REPORT.json exist
  - all five sections present (walk-forward, perturbation, shuffle canary,
    deflated Sharpe, ablation)
  - the shuffle canary passed (edge vanished on shuffled data)
  - a key number in the Markdown matches the JSON (deflated Sharpe ratio)

Run: python cli/verify_falsification.py   (or: make verify-falsification)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
RJSON = REPO / "falsify" / "REPORT.json"
RMD = REPO / "falsify" / "REPORT.md"


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    import tests.test_deflated_sharpe as td
    check(td.main() == 0, "deflated-Sharpe known-answer tests")

    check(RJSON.exists() and RMD.exists(), "REPORT.md and REPORT.json exist")
    if not RJSON.exists():
        print("RESULT: report not generated — run `make falsify` first.")
        return 1
    r = json.loads(RJSON.read_text())
    for sect in ["walk_forward", "perturbation", "shuffle_canary", "deflated_sharpe", "ablation"]:
        check(sect in r, f"section present: {sect}")

    check(r["shuffle_canary"]["edge_survived_shuffle"] is False,
          "shuffle canary passed (edge vanished on shuffled data)")

    md = RMD.read_text()
    dsr = r["deflated_sharpe"]["deflated_sharpe_ratio"]
    check(f"{dsr:.3f}" in md or f"{dsr:.2f}" in md, "deflated Sharpe in MD matches JSON")
    check(len(r["walk_forward"].get("folds", [])) >= 1, "walk-forward produced folds")
    check(len(r["ablation"]["rows"]) >= 1, "ablation covered features")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL FALSIFICATION CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
