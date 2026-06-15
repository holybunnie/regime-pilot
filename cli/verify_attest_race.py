#!/usr/bin/env python3
"""Prove the duplicate-commit race (ids 7/26) is closed. Mock chain only — no network.

Reproduces the exact failure, then shows each guard layer closing it:

  Scenario A  no guards          -> TWO commits (this IS the original id-7/id-26 bug)
  Scenario B  single-flight lock -> exactly ONE commit under concurrent invocation
  Scenario C  on-chain pre-send guard -> a later/separate run skips the already-committed hour

PASS requires A==2 (the simulator really exercises the race), B==1, C==1.

Run: PYTHONPATH=. python cli/verify_attest_race.py   (or: make verify-attest-race)
"""
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from attest import single_flight as sf  # noqa: E402

HOUR = "2026-06-13T13:00:00Z"
HASH = bytes.fromhex("1e9282b1360befb96eb307a2b916c1182ca6cfa00e6d74691ee5f15107bbabb2")


class MockContract:
    """Thread-safe stand-in for SignalAttestor exposing commitCount/getCommit/commit."""
    def __init__(self):
        self._commits = []          # list of 32-byte hashes
        self._lock = threading.Lock()

        class _Fns:
            def __init__(self, outer): self.o = outer
            def commitCount(self): return _Call(lambda: len(self.o._commits))
            def getCommit(self, i): return _Call(lambda: (self.o._commits[i], 0, False))
        self.functions = _Fns(self)

    def commit(self, h):
        # widen the race window the way real network latency would
        time.sleep(0.05)
        with self._lock:
            self._commits.append(h)


class _Call:
    def __init__(self, fn): self.fn = fn
    def call(self): return self.fn()


def worker(contract, use_lock, use_onchain_guard):
    """One hourly run with the chosen guards. Returns 'committed' or 'skipped:<why>'."""
    if use_lock and not sf.acquire_hour_lock(HOUR):
        return "skipped:lock"
    try:
        if use_onchain_guard and sf.onchain_hash_exists(contract, HASH):
            return "skipped:onchain"
        contract.commit(HASH)
        return "committed"
    finally:
        if use_lock:
            sf.release_hour_lock(HOUR)


def run_concurrent(use_lock, use_onchain_guard):
    sf.release_hour_lock(HOUR)  # clean slate
    contract = MockContract()
    out = {}
    threads = [threading.Thread(target=lambda i=i: out.__setitem__(i, worker(
        contract, use_lock, use_onchain_guard))) for i in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    return contract.functions.commitCount().call(), list(out.values())


def main():
    a_count, a_res = run_concurrent(use_lock=False, use_onchain_guard=False)
    b_count, b_res = run_concurrent(use_lock=True, use_onchain_guard=False)

    # Scenario C: a fresh/later run hits a chain that already has the hash
    sf.release_hour_lock(HOUR)
    contract = MockContract()
    contract.commit(HASH)                       # the primary already landed
    c_res = worker(contract, use_lock=True, use_onchain_guard=True)
    c_count = contract.functions.commitCount().call()

    print(f"Scenario A  no guards            -> commits={a_count}  {a_res}")
    print(f"Scenario B  single-flight lock   -> commits={b_count}  {b_res}")
    print(f"Scenario C  on-chain pre-send    -> commits={c_count}  result={c_res}")

    ok = (a_count == 2 and b_count == 1 and c_count == 1 and c_res == "skipped:onchain")
    print("RESULT:", "PASS — race reproduced then closed by both guards" if ok
          else "FAIL — guard did not behave as required")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
