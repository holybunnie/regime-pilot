#!/usr/bin/env python3
"""Items 4 & 7: results are framed honestly, full-window first, with precise timing wording.

Greps README.md and STATUS.md and asserts:
  - the full-window figure (v1 and v2) appears BEFORE the favourable embargo slice (+1.8%)
  - the phrases "no statistically significant" and "single out-of-sample window" are present
  - the overstated phrase "before that hour's outcome is known" is GONE
  - the precise timing phrasing is present (computed strictly before T; outcome not yet realised)
  - the system-first thesis sentence is present

Run: python cli/verify_framing.py   (or: make verify-framing)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SLICE = "+1.8%"


def check(cond, msg, fails):
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        fails.append(msg)


def first_index(text, *needles):
    """Lowest index at which any needle occurs, or -1 if none present."""
    idxs = [text.find(n) for n in needles if text.find(n) != -1]
    return min(idxs) if idxs else -1


def _norm(s):
    """Lowercase + collapse all whitespace so line-wraps don't hide a phrase."""
    return " ".join(s.lower().split())


def main():
    fails = []
    readme = _norm((REPO / "README.md").read_text())
    status = _norm((REPO / "STATUS.md").read_text())

    for name, text in (("README", readme), ("STATUS", status)):
        full_i = first_index(text, "-10.4%", "-10.86%", "-10.9%", "−10.4%", "−10.86%", "−10.9%")
        slice_i = first_index(text, SLICE)
        check(full_i != -1, f"{name}: full-window figure present", fails)
        if slice_i != -1:
            check(full_i != -1 and full_i < slice_i,
                  f"{name}: full-window figure leads the +1.8% slice", fails)
        check("no statistically significant" in text.lower(),
              f"{name}: 'no statistically significant' present", fails)
        check("single out-of-sample window" in text.lower(),
              f"{name}: 'single out-of-sample window' label present", fails)

    # Item 7: overstated wording removed, precise wording present (README)
    check("before that hour's outcome is known" not in readme
          and "before that hour’s outcome is known" not in readme,
          "README: overstated 'before that hour's outcome is known' removed", fails)
    check("strictly before" in readme.lower(),
          "README: precise 'strictly before T' wording present", fails)
    check("outcome is realized" in readme.lower() or "outcome is realised" in readme.lower(),
          "README: precise outcome-realization wording present", fails)

    # system-first thesis
    check("the verification system is the contribution" in readme.lower()
          or "the point is the trustworthy measurement" in readme.lower(),
          "README: system-first thesis present", fails)

    print()
    if fails:
        print(f"FAIL: {len(fails)} framing check(s) failed")
        return 1
    print("ALL FRAMING CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
