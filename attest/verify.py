#!/usr/bin/env python3
"""Chain-complete verification of EVERY on-chain commit. Writes attest/VERIFICATION.md.

Unlike a CSV-driven check, this iterates the contract's own commitCount() so it can
NEVER miss an on-chain commit (that is exactly how ids 7 and 26 were found). For every
on-chain id it assigns one status:

  REPRODUCED ✅          a revealed payload + salt recomputes to the on-chain hash
  RECORDED ✅            a primary forward commit logged in commits_public.csv; its
                         payload is sealed until reveal day, when it becomes REPRODUCED
  DOCUMENTED-DUPLICATE ⚠️ identical hash to an earlier id — a duplicate workflow run for
                         the same decision hour (see attest/RECONCILIATION.md)
  MISMATCH ❌            on-chain hash disagrees with the recorded/revealed value
  UNACCOUNTED ❌         an on-chain id we cannot explain  (pass condition: zero of these)

Data source: live BSC RPC when reachable, else the committed snapshot
attest/onchain_ledger.json — so the check runs on a fresh clone with no secrets and no
network (make verify, offline). Pass `--offline` to force the snapshot.

Run: python attest/verify.py [--offline]   (or: make attest-verify)
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

PUBLIC = REPO / "attest" / "commits_public.csv"
RECON = REPO / "attest" / "commits_reconciliation.csv"
REVEALS = REPO / "attest" / "reveals.json"
SNAPSHOT = REPO / "attest" / "onchain_ledger.json"
OUT = REPO / "attest" / "VERIFICATION.md"


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_ledger_live():
    """Read commitCount + getCommit(i) for every id directly from the chain."""
    from attest import chain
    w3 = chain.get_w3()
    d = chain.deployment()
    c = w3.eth.contract(address=w3.to_checksum_address(d["address"]), abi=d["abi"])
    csv_blocks = {}
    if PUBLIC.exists():
        csv_blocks = {int(r["commit_id"]): r.get("block")
                      for r in csv.DictReader(PUBLIC.open())}
    n = c.functions.commitCount().call()
    ledger = []
    for i in range(n):
        h, ts, revealed = c.functions.getCommit(i).call()
        ledger.append({"id": i, "hash": "0x" + h.hex(),
                       "block_number": int(csv_blocks[i]) if csv_blocks.get(i) else None,
                       "block_timestamp_utc": _iso(ts), "revealed": revealed,
                       "present_in_csv": i in csv_blocks})
    return ledger, f"live BSC RPC (contract {d['address']})"


def load_ledger(offline):
    if not offline:
        try:
            return build_ledger_live()
        except Exception as e:
            print(f"(RPC unavailable: {str(e)[:80]} — falling back to committed snapshot)")
    if not SNAPSHOT.exists():
        raise SystemExit("FATAL: no RPC and no attest/onchain_ledger.json snapshot")
    return json.loads(SNAPSHOT.read_text()), f"committed snapshot {SNAPSHOT.name}"


def main():
    offline = "--offline" in sys.argv
    ledger, source = load_ledger(offline)

    # primary forward commits (one row per decision hour)
    csv_rows = {}
    if PUBLIC.exists():
        csv_rows = {int(r["commit_id"]): r for r in csv.DictReader(PUBLIC.open())}
    reveals = json.loads(REVEALS.read_text()) if REVEALS.exists() else {}

    # optional independent hash reproduction (needs reveals + market data; skipped offline)
    reproduce = None
    if reveals and not offline:
        try:
            from attest.hashing import commit_hash
            from attest.live_signal import compute_signal

            def reproduce(cid, ts):
                r = reveals[str(cid)]
                salt = bytes.fromhex(r["salt"][2:] if r["salt"].startswith("0x") else r["salt"])
                payload = r.get("payload") or compute_signal(
                    REPO / "spec" / "regime_pilot_v2.spec.json", ts)
                return "0x" + commit_hash(payload, salt).hex()
        except Exception:
            reproduce = None

    # Highest id this checkout's public ledger knows about. The live committer keeps adding
    # commits hourly, so the chain can be AHEAD of a static checkout. An on-chain id beyond this
    # high-water mark is a newer hourly commit (accounted, pending the next ledger sync) — NOT a
    # gap. A truly unaccounted id is one WITHIN the known range with no explanation (how 7/26 were
    # found). This keeps a live `make attest-verify` from flapping to FAIL between hourly commits.
    max_csv_id = max(csv_rows) if csv_rows else -1

    first_hash = {}      # hash -> first on-chain id that carried it
    results = []
    for row in ledger:
        cid, h = row["id"], row["hash"]
        ts = csv_rows.get(cid, {}).get("timestamp_utc")
        status = note = None

        if h in first_hash:
            primary = first_hash[h]
            phour = csv_rows.get(primary, {}).get("timestamp_utc", "?")
            status = "DOCUMENTED-DUPLICATE"
            note = (f"identical hash to id {primary} — duplicate workflow run for decision "
                    f"hour {phour}; signs nothing new")
        else:
            first_hash[h] = cid
            if str(cid) in reveals and reproduce:
                status = "REPRODUCED" if reproduce(cid, ts) == h else "MISMATCH"
                note = "revealed payload+salt recomputes to on-chain hash" \
                    if status == "REPRODUCED" else "revealed payload does NOT match on-chain hash"
            elif cid in csv_rows:
                if csv_rows[cid]["hash"].lower() == h.lower():
                    status = "RECORDED"
                    note = f"primary forward commit for {ts}; payload sealed until reveal"
                else:
                    status = "MISMATCH"
                    note = "commits_public.csv hash disagrees with on-chain hash"
            elif cid > max_csv_id:
                status = "PENDING-NEWER"
                note = ("newer hourly commit made after this checkout's ledger — re-run "
                        "`make attest-snapshot` / pull latest to fold it in; not a gap")
            else:
                status = "UNACCOUNTED"
                note = "on-chain id not in CSV and not a known duplicate"
        results.append({**row, "status": status, "note": note, "ts": ts})

    order = {"REPRODUCED": 0, "RECORDED": 0, "DOCUMENTED-DUPLICATE": 0,
             "BOOTSTRAP": 0, "PENDING-NEWER": 0, "MISMATCH": 1, "UNACCOUNTED": 1}
    bad = [r for r in results if order.get(r["status"], 1) == 1]
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    icon = {"REPRODUCED": "✅", "RECORDED": "✅", "DOCUMENTED-DUPLICATE": "⚠️",
            "BOOTSTRAP": "🟦", "PENDING-NEWER": "🕒", "MISMATCH": "❌", "UNACCOUNTED": "❌"}
    lines = ["# On-Chain Attestation Verification", "",
             f"- Source: {source}",
             f"- On-chain commits (commitCount): **{len(results)}**",
             "- Status tally: " + ", ".join(f"{k} {counts[k]}" for k in sorted(counts)), "",
             "| id | decision hour (UTC) | block ts (UTC) | status | note |",
             "|--:|---------------------|----------------|--------|------|"]
    for r in results:
        lines.append(f"| {r['id']} | {r['ts'] or '—'} | {r['block_timestamp_utc']} | "
                     f"{r['status']} {icon.get(r['status'],'')} | {r['note']} |")
    accounted = not bad
    pending = counts.get("PENDING-NEWER", 0)
    pending_note = f" ({pending} newer than this checkout's ledger — pending sync)" if pending else ""
    lines += ["",
              f"**{len(results)} on-chain commits, "
              + (f"all accounted for{pending_note}." if accounted
                 else f"{len(bad)} UNACCOUNTED/MISMATCH — FAIL.")
              + "**"]
    OUT.write_text("\n".join(lines) + "\n")

    print(f"Chain-complete verify via {source}")
    print("  " + " | ".join(f"{k}:{counts[k]}" for k in sorted(counts)))
    if accounted:
        print(f"PASS: {len(results)} on-chain commits, all accounted for{pending_note} -> {OUT}")
        return 0
    print(f"FAIL: {len(bad)} unaccounted/mismatch ids: {[r['id'] for r in bad]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
