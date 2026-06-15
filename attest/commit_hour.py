#!/usr/bin/env python3
"""Commit one hourly signal to the on-chain SignalAttestor (BSC mainnet).

Flow each run:
  1. refresh market data (incremental)
  2. compute the frozen flagship's signal for the latest decision hour
  3. salt = deterministic_salt(seed, timestamp); hash = keccak(canonical_json || salt)
  4. skip if this decision hour was already committed (idempotent)
  5. send commit(hash) on-chain
  6. append the public record to attest/commits_public.csv (hash + tx, safe to push)
     and a private mirror to attest/log.jsonl (gitignored)
  7. update attest/heartbeat.txt

Designed for an hourly GitHub Actions cron. On data/RPC failure it logs a MISSED slot
and exits non-zero (the gap in commit timestamps is the honest record of the miss).

Run: python attest/commit_hour.py   (or: make attest-commit)
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from attest import chain                                       # noqa: E402
from attest.hashing import commit_hash, canonical_json, deterministic_salt  # noqa: E402
from attest.live_signal import compute_signal                  # noqa: E402
from attest.single_flight import (acquire_hour_lock,           # noqa: E402
                                  release_hour_lock, onchain_hash_exists)

# Frozen spec attested going forward. Switched v1 -> v2 (long/short) on 2026-06-13.
# Past v1 commits stay verifiable: attest/verify.py matches each commit to whichever
# spec reproduces its on-chain hash.
SPEC = REPO / "spec" / "regime_pilot_v2.spec.json"
LOG = REPO / "attest" / "log.jsonl"
PUBLIC = REPO / "attest" / "commits_public.csv"
HEARTBEAT = REPO / "attest" / "heartbeat.txt"
MISSED = REPO / "attest" / "missed.log"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def already_committed(timestamp_utc):
    if not PUBLIC.exists():
        return False
    with PUBLIC.open() as f:
        return any(row.get("timestamp_utc") == timestamp_utc for row in csv.DictReader(f))


def append_public(rec):
    new = not PUBLIC.exists()
    with PUBLIC.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp_utc", "commit_id", "hash", "tx", "block", "regime"])
        if new:
            w.writeheader()
        w.writerow(rec)


def log_missed(reason):
    with MISSED.open("a") as f:
        f.write(f"{now_iso()}\tMISSED\t{reason}\n")


def main():
    env = chain.load_env()
    seed = env.get("ATTEST_SALT_SEED", "").strip()
    if not seed:
        print("FATAL: ATTEST_SALT_SEED not set — cannot make reproducible commits.")
        return 1
    locked_hour = None
    try:
        # 1) refresh data
        import importlib
        fetch = importlib.import_module("engine.data.fetch")
        fetch.main()
        # 2) signal
        payload = compute_signal(SPEC)
        ts = payload["timestamp_utc"]
        if already_committed(ts):
            print(f"Hour {ts} already committed — nothing to do (idempotent).")
            HEARTBEAT.write_text(f"{now_iso()} alive; last decision {ts}; no-op (already committed)\n")
            return 0
        # single-flight: only the first run for this decision hour proceeds (stops the
        # id-7/id-26 duplicate race). A concurrent second run fails to acquire and exits.
        if not acquire_hour_lock(ts):
            print(f"Another run holds hour {ts} — skipping (single-flight lock).")
            return 0
        locked_hour = ts
        # 3) salt + hash
        salt = deterministic_salt(seed, ts)
        h = commit_hash(payload, salt)
        # 5) on-chain commit
        w3 = chain.get_w3()
        acct = chain.get_account()
        d = chain.deployment()
        if not d:
            print("FATAL: no deployment.json — deploy the contract first.")
            return 1
        c = w3.eth.contract(address=w3.to_checksum_address(d["address"]), abi=d["abi"])
        # authoritative pre-send guard: never double-commit a hour already on-chain.
        # Holds even across cancelled/separate runners where the local lock cannot help.
        if onchain_hash_exists(c, h):
            print(f"Hour {ts} already committed on-chain (hash present) — skipping.")
            HEARTBEAT.write_text(f"{now_iso()} alive; last decision {ts}; no-op (already on-chain)\n")
            return 0
        rcpt = chain.send_tx(w3, acct, {"to": c.address,
                                        "data": c.encode_abi("commit", [h])})
        ev = c.events.Committed().process_receipt(rcpt)[0]["args"]
        cid = ev["id"]
        txh = "0x" + rcpt["transactionHash"].hex().lstrip("0x")
    except Exception as e:
        print(f"MISSED this slot: {e}")
        log_missed(str(e).replace("\n", " ")[:200])
        return 1
    finally:
        if locked_hour is not None:
            release_hour_lock(locked_hour)

    # 6) records
    append_public({"timestamp_utc": ts, "commit_id": cid, "hash": "0x" + h.hex(),
                   "tx": txh, "block": rcpt["blockNumber"], "regime": payload["regime"]})
    with LOG.open("a") as f:
        f.write(json.dumps({"commit_id": cid, "timestamp_utc": ts, "regime": payload["regime"],
                            "payload": payload, "salt": "0x" + salt.hex(), "tx": txh,
                            "block": rcpt["blockNumber"], "committed_at": now_iso(),
                            "canonical": canonical_json(payload).decode()}) + "\n")
    HEARTBEAT.write_text(f"{now_iso()} alive; committed id={cid} hour={ts} regime={payload['regime']}\n")
    print(f"COMMITTED ✅ id={cid} hour={ts} regime={payload['regime']} "
          f"hash=0x{h.hex()[:16]}… tx={txh}")
    print(f"BscScan: https://bscscan.com/tx/{txh}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
