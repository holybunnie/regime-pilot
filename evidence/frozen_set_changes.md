# FROZEN SET — approved changes log

The baseline of every live-committer runtime file is `frozen_set_baseline.txt` (recorded
before any work). This file logs the **only** operator-approved exception.

## 1. attest/commit_hour.py — guard-only change (Item 2), operator-approved

**Approval:** operator chose "Wire guard, keep queue setting" (Item 2, Option 1).

| | sha256 |
|---|---|
| before (baseline) | `1d758e218f023cb8dd8017e8b6f001def66a07895ade82fe7d2d1a0ba56566cd` |
| after (approved)  | `797d7fea4e4559417592b674dc9b31affc90ec7a9c4e37d1f850e7fc01f854f3` |

**What changed:** added a single-flight lockfile acquire/release and an on-chain pre-send
duplicate guard, so a second hourly run for the same decision hour exits without committing.
**What did NOT change — the signal's meaning/hash:** the lines that compute the signal and the
on-chain hash are byte-identical:
- `payload = compute_signal(SPEC)`
- `salt = deterministic_salt(seed, ts)`
- `h = commit_hash(payload, salt)`
- `c.encode_abi("commit", [h])`

Proof: `diff -u` shows only added guard blocks (import, `locked_hour`, lock acquire, on-chain
guard, `finally` release). The committer still signs exactly the same hash for any given hour.

## 2. All other 12 frozen-set files — byte-identical

`.github/workflows/attest.yml` was **not** changed (Option 1 keeps `cancel-in-progress: false`).
Every other frozen file matches `frozen_set_baseline.txt` exactly. Verify:

    sha256sum -c evidence/frozen_set_baseline.txt   # 12 OK; commit_hour.py is the approved change above
