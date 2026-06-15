#!/usr/bin/env python3
"""Regenerate the committed on-chain ledger snapshot (attest/onchain_ledger.json), READ-ONLY.

The live hourly committer keeps adding commits to the chain, so the snapshot that backs the
OFFLINE verifier (`make attest-verify` with no RPC) must be refreshed periodically or it lags the
chain and reports the newest ids as UNACCOUNTED. This script reads `commitCount()` + `getCommit(i)`
for every id directly from BSC mainnet and rewrites the snapshot. It sends NO transactions.

Run: PYTHONPATH=. python attest/snapshot_ledger.py   (or: make attest-snapshot)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from attest.verify import SNAPSHOT, build_ledger_live  # noqa: E402


def main():
    ledger, source = build_ledger_live()
    SNAPSHOT.write_text(json.dumps(ledger, indent=2) + "\n")
    present = sum(1 for r in ledger if r["present_in_csv"])
    print(f"Refreshed {SNAPSHOT.name} from {source}")
    print(f"  {len(ledger)} on-chain ids (0..{ledger[-1]['id']}); "
          f"{present} present_in_csv, {len(ledger) - present} not (duplicates/awaiting CSV row)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
