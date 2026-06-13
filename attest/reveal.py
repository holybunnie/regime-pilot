#!/usr/bin/env python3
"""Reveal commits: publish payloads+salts and (optionally) call reveal() on-chain.

Generates two files:
  - attest/reveals.json            : { id: {payload, salt, timestamp_utc} }  (used by verify.py)
  - attest/revealed_payloads.json  : same, the public artifact to commit at reveal time

With --onchain it also batches reveal(id, payloadURI, salt) transactions on BSC mainnet.
Without it (default), it only produces the files so verification can run off-chain — the
on-chain reveal is optional proof and costs gas.

Run: python attest/reveal.py [--onchain]   (or: make attest-reveal)
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from attest import chain                                       # noqa: E402
from attest.hashing import deterministic_salt, commit_hash    # noqa: E402
from attest.live_signal import compute_signal                 # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SPECS = [REPO / "spec" / "regime_pilot.spec.json",
         REPO / "spec" / "regime_pilot_v2.spec.json"]
PUBLIC = REPO / "attest" / "commits_public.csv"
REVEALS = REPO / "attest" / "reveals.json"
PUBLISHED = REPO / "attest" / "revealed_payloads.json"
PAYLOAD_URI = "https://github.com/holybunnie/regime-pilot/blob/main/attest/revealed_payloads.json"


def main(onchain=False):
    seed = chain.load_env().get("ATTEST_SALT_SEED", "").strip()
    if not seed:
        print("FATAL: ATTEST_SALT_SEED required to regenerate salts.")
        return 1
    rows = list(csv.DictReader(PUBLIC.open()))
    w3 = chain.get_w3()
    d = chain.deployment()
    c = w3.eth.contract(address=w3.to_checksum_address(d["address"]), abi=d["abi"])
    reveals = {}
    for row in rows:
        ts = row["timestamp_utc"]
        cid = row["commit_id"]
        salt = deterministic_salt(seed, ts)
        onchain_hash, _, _ = c.functions.getCommit(int(cid)).call()
        target = "0x" + onchain_hash.hex()
        # pick the spec that reproduces this commit's on-chain hash (handles v1->v2)
        payload = next((p for sp in SPECS for p in [compute_signal(sp, ts)]
                        if ("0x" + commit_hash(p, salt).hex()) == target),
                       compute_signal(SPECS[-1], ts))
        reveals[cid] = {"payload": payload, "salt": "0x" + salt.hex(), "timestamp_utc": ts}
    REVEALS.write_text(json.dumps(reveals, indent=2, sort_keys=True))
    PUBLISHED.write_text(json.dumps(reveals, indent=2, sort_keys=True))
    print(f"Wrote {len(reveals)} reveals -> {REVEALS} and {PUBLISHED}")

    if onchain:
        w3 = chain.get_w3()
        acct = chain.get_account()
        d = chain.deployment()
        c = w3.eth.contract(address=w3.to_checksum_address(d["address"]), abi=d["abi"])
        revealed = 0
        for cid, r in reveals.items():
            _, _, already = c.functions.getCommit(int(cid)).call()
            if already:
                continue
            data = c.encode_abi("reveal", [int(cid), PAYLOAD_URI, bytes.fromhex(r["salt"][2:])])
            chain.send_tx(w3, acct, {"to": c.address, "data": data})
            revealed += 1
            print(f"  revealed id={cid} on-chain")
        print(f"On-chain reveals sent: {revealed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(onchain="--onchain" in sys.argv))
