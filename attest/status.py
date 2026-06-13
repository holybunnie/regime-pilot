#!/usr/bin/env python3
"""One-line attestation status: liveness + commit count + last commit.

Run: python attest/status.py   (or: make attest-status)
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "attest" / "commits_public.csv"
HEARTBEAT = REPO / "attest" / "heartbeat.txt"
MISSED = REPO / "attest" / "missed.log"


def main():
    n = last = "—"
    if PUBLIC.exists():
        rows = list(csv.DictReader(PUBLIC.open()))
        n = len(rows)
        last = rows[-1]["timestamp_utc"] if rows else "—"
    missed = sum(1 for _ in MISSED.open()) if MISSED.exists() else 0
    alive = "unknown"
    if HEARTBEAT.exists():
        hb = HEARTBEAT.read_text().split()[0]
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(hb.replace("Z", "+00:00")))
            mins = age.total_seconds() / 60
            alive = f"alive {mins:.0f} min ago" if mins < 130 else f"STALE ({mins/60:.1f}h ago)"
        except Exception:
            alive = "heartbeat unreadable"
    d = (REPO / "attest" / "deployment.json")
    addr = "(not deployed)"
    if d.exists():
        import json
        addr = json.loads(d.read_text())["address"]
    print(f"ATTEST: {alive} | commits={n} | last={last} | missed={missed} | contract={addr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
