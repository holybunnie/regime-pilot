#!/usr/bin/env python3
"""Single-flight guards that stop two hourly runs from double-committing one decision hour.

This is the fix for the id-7 / id-26 duplicate commits (see attest/RECONCILIATION.md). It is
deliberately a SEPARATE module so it can be unit-tested in isolation and wired into the live
committer with a minimal, reviewable diff. It changes only WHETHER/WHEN a commit fires — never
the signal contents or the hash.

Two independent layers (defence in depth):

1. acquire_hour_lock(hour): an atomic O_CREAT|O_EXCL lockfile keyed by the decision hour.
   Only the first process for that hour wins; a concurrent second process fails to acquire and
   exits without committing. Released after the CSV record is written (or on crash via stale-age
   reclaim, so a dead run never wedges the hour forever).

2. onchain_hash_exists(contract, h): the authoritative guard. Before sending, re-read the chain
   for an existing commit carrying this exact hash. Because the hash is deterministic for a
   decision hour, a matching hash means this hour was already committed — so skip. This holds
   even across separate machines / cancelled runners where a local lock cannot help.
"""
import errno
import os
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOCK_DIR = REPO / "attest" / ".locks"
STALE_SECONDS = 1800  # a lock older than this is presumed abandoned by a dead runner


def _lock_path(hour: str) -> Path:
    safe = hour.replace(":", "").replace("-", "").replace("T", "").replace("Z", "")
    return LOCK_DIR / f"hour_{safe}.lock"


def acquire_hour_lock(hour: str) -> bool:
    """Try to claim the decision hour. Returns True if THIS process won, False if already held."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    p = _lock_path(hour)
    # reclaim a stale lock left by a crashed run
    try:
        if p.exists() and (time.time() - p.stat().st_mtime) > STALE_SECONDS:
            p.unlink()
    except FileNotFoundError:
        pass
    try:
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise
    with os.fdopen(fd, "w") as f:
        f.write(f"{os.getpid()} {int(time.time())}\n")
    return True


def release_hour_lock(hour: str) -> None:
    try:
        _lock_path(hour).unlink()
    except FileNotFoundError:
        pass


def onchain_hash_exists(contract, target_hash: bytes, window: int = 24) -> bool:
    """True if `target_hash` is already an on-chain commit. Authoritative pre-send guard.

    Scans the most recent `window` commits (cheap, bounded) and falls back to a full scan if
    needed. `contract` is any object exposing commitCount() and getCommit(i) returning a tuple
    whose first element is the 32-byte hash (the real web3 contract, or a test double)."""
    n = contract.functions.commitCount().call()
    lo = max(0, n - window)
    for i in range(n - 1, lo - 1, -1):
        if bytes(contract.functions.getCommit(i).call()[0]) == target_hash:
            return True
    # bounded recent window missed it — full scan to be certain (rare path)
    for i in range(lo - 1, -1, -1):
        if bytes(contract.functions.getCommit(i).call()[0]) == target_hash:
            return True
    return False
