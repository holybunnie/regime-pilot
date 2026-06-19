#!/usr/bin/env python3
"""Attestation verification: attestation system.

  - hash known-answer + full local mock-chain commit->reveal->verify pass
  - contract is deployed on BSC mainnet and has live code
  - at least one hourly commit exists
  - every on-chain commit's hash is reproducible from public data (verify.py)

Run: python cli/verify_attestation.py   (or: make verify-attestation)
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    # 1) hash KAT + mock chain
    import tests.test_attest as ta
    check(ta.main() == 0, "hash known-answer + local mock-chain commit/reveal/verify")

    # 2) deployment live on-chain
    from attest import chain
    d = chain.deployment()
    if not d:
        check(False, "deployment.json present")
    else:
        w3 = chain.get_w3()
        code = w3.eth.get_code(w3.to_checksum_address(d["address"]))
        check(len(code) > 3, f"contract live on BSC mainnet at {d['address']}")

    # 3) commits exist
    pub = REPO / "attest" / "commits_public.csv"
    if pub.exists():
        with pub.open() as handle:
            n = len(list(csv.DictReader(handle)))
    else:
        n = 0
    check(n >= 1, f"hourly commits recorded ({n})")

    # 4) every commit reproducible + matches chain
    import attest.verify as v
    check(v.main(["--no-write"]) == 0, "all on-chain hashes reproduced from public data")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL ATTESTATION CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
