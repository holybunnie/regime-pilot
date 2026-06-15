#!/usr/bin/env python3
"""Phase 7 verification: hash recipe + full local commit->reveal->verify on a mock chain.

Uses eth-tester (in-memory EVM) with the REAL compiled SignalAttestor bytecode, so the
exact contract that will go to BSC mainnet is exercised here first — no real funds.

Run: python tests/test_attest.py   (exit 0 = pass)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from attest.hashing import canonical_json, commit_hash, new_salt   # noqa: E402

# Known-answer: fixed payload + fixed salt -> fixed keccak (locked, recomputed independently).
KAT_PAYLOAD = {"regime": "chop", "spec_version": "1.0.0", "timestamp_utc": "2026-06-13T08:00:00Z"}
KAT_SALT = bytes.fromhex("00" * 31 + "01")
KAT_HASH = "0x7afc73b86475e098f34b1cc785196adcbb5277c37a5f9a4c99c86f76afe5146b"


def check_kat():
    h = "0x" + commit_hash(KAT_PAYLOAD, KAT_SALT).hex()
    ok = h == KAT_HASH
    print(f"  [{'PASS' if ok else 'FAIL'}] hash known-answer: {h[:18]}…")
    return ok


def check_canonical_key_order():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    ok = a == b == b'{"a":2,"b":1}'
    print(f"  [{'PASS' if ok else 'FAIL'}] canonical JSON is key-order independent")
    return ok


def check_salt_length():
    ok = len(new_salt()) == 32
    print(f"  [{'PASS' if ok else 'FAIL'}] salt is 32 bytes")
    return ok


def check_mock_chain():
    from web3 import Web3, EthereumTesterProvider
    art = json.loads((REPO / "attest" / "build" / "SignalAttestor.json").read_text())
    w3 = Web3(EthereumTesterProvider())
    owner = w3.eth.accounts[0]
    other = w3.eth.accounts[1]

    C = w3.eth.contract(abi=art["abi"], bytecode=art["bin"])
    tx = C.constructor().transact({"from": owner})
    addr = w3.eth.wait_for_transaction_receipt(tx)["contractAddress"]
    inst = w3.eth.contract(address=addr, abi=art["abi"])

    # build a real signal payload + salt + hash
    payload = {"spec_version": "1.0.0", "spec_hash": "deadbeef",
               "timestamp_utc": "2026-06-13T08:00:00Z", "regime": "trend_up",
               "target_weights": {"BTC": 0.08, "ETH": 0.08}}
    salt = new_salt()
    h = commit_hash(payload, salt)

    # commit
    rcpt = w3.eth.wait_for_transaction_receipt(inst.functions.commit(h).transact({"from": owner}))
    ev = inst.events.Committed().process_receipt(rcpt)[0]["args"]
    cid = ev["id"]
    onchain_hash, ts, revealed = inst.functions.getCommit(cid).call()
    checks = [
        (onchain_hash == h, "on-chain hash equals locally-computed hash"),
        (ts > 0, "commit carries a block timestamp"),
        (not revealed, "commit starts unrevealed"),
    ]

    # owner-only enforcement
    try:
        inst.functions.commit(h).transact({"from": other})
        checks.append((False, "non-owner commit correctly rejected"))
    except Exception:
        checks.append((True, "non-owner commit correctly rejected"))

    # reveal + verify
    inst.functions.reveal(cid, "ipfs://payload", salt).transact({"from": owner})
    _, _, revealed2 = inst.functions.getCommit(cid).call()
    checks.append((revealed2, "commit marked revealed after reveal"))

    # the verifier step: recompute hash from revealed payload+salt, compare to chain
    recomputed = commit_hash(payload, salt)
    checks.append((recomputed == onchain_hash, "verifier recomputes matching hash from reveal"))

    ok = all(c for c, _ in checks)
    for c, msg in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] mock-chain: {msg}")
    return ok


# pytest entrypoints: assert the helper results so `pytest` collects + checks them cleanly
def test_kat(): assert check_kat()
def test_canonical_key_order(): assert check_canonical_key_order()
def test_salt_length(): assert check_salt_length()
def test_mock_chain(): assert check_mock_chain()


def main():
    results = [check_kat(), check_canonical_key_order(), check_salt_length(), check_mock_chain()]
    print()
    if all(results):
        print("ALL ATTESTATION TESTS PASS")
        return 0
    print("FAIL: one or more attestation tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
