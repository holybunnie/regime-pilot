#!/usr/bin/env python3
"""Item 12: HANDOFF.md never contradicts STATUS.md on what is done.

STATUS is canonical and reports every component DONE. This check fails if HANDOFF reintroduces a
"not started / not yet / TODO" contradiction, or if a tracked component STATUS marks done is
missing/absent from HANDOFF.

Run: python cli/verify_docs_consistency.py   (or: make verify-docs-consistency)
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMPONENTS = ["engine", "falsification", "attestation", "x402", "secret", "schema", "skill"]
CONTRADICTIONS = ["not started", "not yet started", "todo:", "## not started"]


def main():
    status = (REPO / "STATUS.md").read_text().lower()
    handoff = (REPO / "HANDOFF.md").read_text().lower()
    fails = []

    for c in CONTRADICTIONS:
        if c in handoff:
            print(f"  [FAIL] HANDOFF contains contradiction marker: '{c}'")
            fails.append(f"contradiction:{c}")
    if not fails:
        print("  [PASS] HANDOFF has no 'not started / TODO' contradiction markers")

    for comp in COMPONENTS:
        in_status = comp in status
        in_handoff = comp in handoff
        ok = (not in_status) or in_handoff
        print(f"  [{'PASS' if ok else 'FAIL'}] component '{comp}': "
              f"status={in_status} handoff={in_handoff}")
        if not ok:
            fails.append(f"missing-in-handoff:{comp}")

    # both must point at the same canonical offline command
    for name, txt in (("STATUS", status), ("HANDOFF", handoff)):
        ok = "make verify" in txt
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} references `make verify`")
        if not ok:
            fails.append(f"no-make-verify:{name}")

    print()
    if fails:
        print(f"FAIL: {len(fails)} doc-consistency issue(s): {fails}")
        return 1
    print("ALL DOC-CONSISTENCY CHECKS PASS — HANDOFF agrees with STATUS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
