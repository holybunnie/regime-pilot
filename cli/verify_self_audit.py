#!/usr/bin/env python3
"""Gate: SELF_AUDIT.md exists, poses 10 hostile questions, and answers each with a residual risk.

A mandate requirement: prove we red-teamed our own submission. This checks structure, not prose
quality — it fails loudly if the document is missing questions or drops the residual-risk honesty.
"""
import re
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "SELF_AUDIT.md"


def main():
    if not DOC.exists():
        print("[FAIL] SELF_AUDIT.md missing")
        return 1
    text = DOC.read_text()
    questions = re.findall(r"^## Q(\d+)\.", text, re.MULTILINE)
    nums = sorted(int(n) for n in questions)
    residuals = len(re.findall(r"\*\*Residual risk\.\*\*", text))
    answers = len(re.findall(r"\*\*Answer\.\*\*", text))

    ok = True
    if nums != list(range(1, 11)):
        print(f"[FAIL] expected questions Q1..Q10, found {nums}")
        ok = False
    if answers < 10:
        print(f"[FAIL] expected >=10 '**Answer.**' blocks, found {answers}")
        ok = False
    if residuals < 10:
        print(f"[FAIL] expected >=10 '**Residual risk.**' blocks, found {residuals}")
        ok = False

    if ok:
        print(f"[PASS] SELF_AUDIT.md: {len(nums)} hostile questions, "
              f"{answers} answers, {residuals} residual-risk disclosures")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
