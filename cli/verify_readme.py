#!/usr/bin/env python3
"""Verify that README is self-contained, accurate, and system-first.

Asserts every required judge-facing section is present, the system-first thesis leads, and the
old "matches live Binance" headline claim is gone (reworded as a generic source-tolerance claim).

Run: python cli/verify_readme.py   (or: make verify-readme)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _norm(s):
    return " ".join(s.lower().split())


# (label, mode, needles): mode "all" -> every needle present; "any" -> at least one present.
REQUIRED = [
    ("system-first thesis", "any", ["the verification system is the contribution",
                                    "the point is the trustworthy measurement"]),
    ("problem section", "all", ["## the problem it solves"]),
    ("architecture diagram", "all", ["## how it works", "signalattestor.sol"]),
    ("differentiator section", "all", ["## the differentiator", "commit_hash = keccak256"]),
    ("honest results, full-window first", "all", ["## results, honestly", "full-window result"]),
    ("design decisions", "all", ["## design decisions"]),
    ("honest limitations", "all", ["## honest limitations"]),
    ("reproduce-yourself", "all", ["## reproduce it yourself", "make verify-full"]),
    ("x402 plan", "all", ["## x402 data-cost plan"]),
    ("reveal runbook", "all", ["## reveal runbook", "make attest-reveal"]),
]
FORBIDDEN = [
    "matches live binance",
    "user-invocable",
    "free cmc tier",
    "cmc free tier",
    "waiting on the team",
]


def main():
    txt = _norm((REPO / "README.md").read_text())
    fails = []
    for label, mode, needles in REQUIRED:
        ok = all(n in txt for n in needles) if mode == "all" else any(n in txt for n in needles)
        print(f"  [{'PASS' if ok else 'FAIL'}] section present: {label}")
        if not ok:
            fails.append(label)
    for f in FORBIDDEN:
        ok = f not in txt
        print(f"  [{'PASS' if ok else 'FAIL'}] forbidden claim absent: '{f}'")
        if not ok:
            fails.append(f"forbidden:{f}")
    print()
    if fails:
        print(f"FAIL: {len(fails)} README check(s) failed: {fails}")
        return 1
    print("ALL README CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
