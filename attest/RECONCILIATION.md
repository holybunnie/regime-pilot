# Reconciliation of on-chain commits 7 and 26

**Plain-English summary:** On-chain commit ids **7** and **26** are harmless **exact
duplicates** of the commits immediately before them (ids 6 and 25). Each duplicate carries a
**byte-identical hash** to its primary and was posted about three minutes later by a second
GitHub Actions run that fired for the *same decision hour*. They publish nothing new and
contradict nothing. No altered or competing prediction was ever committed. This is why they do
not appear as separate rows in `commits_public.csv` (which records one row per decision hour).

## The evidence (read-only, no transactions sent)

| primary id | duplicate id | shared hash | primary block ts | duplicate block ts | gap |
|--:|--:|---|---|---|---|
| 6 | 7 | `0x1e9282b1360befb96eb307a2b916c1182ca6cfa00e6d74691ee5f15107bbabb2` | 2026-06-13T13:03:24Z | 2026-06-13T13:06:45Z | 3m21s |
| 25 | 26 | `0x5e09d4edda10a6c8b26456d035c0c102c12c787c53f29735dbc5fd8ab018c6e0` | 2026-06-14T07:03:52Z | 2026-06-14T07:07:23Z | 3m31s |

Full per-id ledger: [`onchain_ledger.json`](onchain_ledger.json), regenerated directly from the
contract's own `commitCount()` (the chain grows by one commit per hour). The only two ids absent
from `commits_public.csv` are 7 and 26, both documented here.

## Why identical hashes prove they are duplicates (not tampering)

The committed value is `keccak256(canonical_json(signal) || salt)` where
`salt = keccak256(seed || decision_hour)`. The salt is derived **only** from the secret seed
and the decision-hour timestamp — not from wall-clock time or run id. Therefore two runs for the
**same decision hour** with the **same frozen spec and data** produce the **same signal**, the
**same salt**, and the **same hash**. An identical on-chain hash is only possible if both runs
committed the *same prediction for the same hour*. id 7 == id 6 and id 26 == id 25 at the byte
level, so each pair is one prediction stamped twice. (A tampered or different prediction would
necessarily have produced a different hash.) The primaries' decision hours are recorded in
`commits_public.csv`: id 6 → `2026-06-13T13:00:00Z`, id 25 → `2026-06-14T07:00:00Z`.

## Root cause

Idempotency was checked against `commits_public.csv` ("is this decision hour already a row?").
That row is written and pushed only *after* the on-chain send. Two overlapping hourly runs for
one decision hour both passed the "not recorded yet" check and both sent. The workflow's
`concurrency.cancel-in-progress: false` queued the second run instead of cancelling it, so it
executed later and double-stamped. Fixed in **Item 2** by a single-flight hour lock plus a
pre-send on-chain duplicate guard (`onchain_hash_exists`), so a queued second run becomes a
harmless no-op. We deliberately **keep `cancel-in-progress: false`** — no run is ever cancelled
mid-transaction; the guards (not cancellation) are what make a duplicate impossible.

## Disclosure

Rather than hide them, both duplicates are listed in
[`commits_reconciliation.csv`](commits_reconciliation.csv) with a `note`, surfaced in the
generated [`VERIFICATION.md`](VERIFICATION.md) as `DOCUMENTED-DUPLICATE ⚠️`, and the chain-complete
verifier (`make attest-verify`) iterates the contract's own `commitCount()` so no on-chain id can
ever go unlisted again. Pass condition: zero UNACCOUNTED ids.
