# FROZEN SET — approved changes log

The baseline of every live-committer runtime file is `frozen_set_baseline.txt` (recorded
before any work). This file logs every operator-approved exception.

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

## 2. engine/backtest.py — contract hardening with legacy-result compatibility

**Approval:** operator requested the comprehensive audit fixes while explicitly requiring that the
hourly cron continue uninterrupted.

| | sha256 |
|---|---|
| before (baseline) | `b7390788fdd458fc26b41b8fe233766f6b35f180a6e9b0f18e07dc9ca5f29105` |
| after (approved)  | `b6f6eb071444d8e5a68c96fc211359efd443cc3ec48c0565bc52d107188c6869` |

**Correctness-only changes:**
- Validate every spec before execution.
- Apply explicit symbol allow-lists and exclusions.
- Make unsupported ranking fail instead of silently falling back.
- Use the no-lookahead accessor in asset availability checks.
- Enforce `max_gross_exposure` after every action, including staged re-entry.
- Accept CMC's normalized `volume_24h_usd` without multiplying or rolling it again.
- Load BTC benchmark data even when an explicit trade universe excludes BTC.

**What did NOT change:** the active v1/v2 strategy meaning, Binance cache interpretation, regime
logic, sizing law, costs, fills, or signal hash recipe. `tests/test_engine_compat.py` regenerates
three deterministic synthetic runs using a baseline captured from the pre-fix engine and requires
byte-derived result hashes for the momentum example, v1, and live v2 to remain identical. The CMC
adapter writes a separate inactive cache and is not selected by the hourly workflow.

## 3. engine/data/fetch.py — wording cleanup only

| | sha256 |
|---|---|
| before (baseline) | `b46fc8cfa155304d7fa86cf80498b3b4923781cb0ebe8a73dd48f3223240d2c9` |
| after (approved)  | `faef3036886999244c28311ad21f7177cec345023e95c1baf7417e9f64aa4dbc` |

Only the module docstring changed. Fetch endpoints, parameters, cache behavior, credentials,
timestamps, and all executable statements are byte-identical.

## 4. Hourly workflow — verification snapshot auto-refresh

**File:** `.github/workflows/attest.yml`

**Approved hash:** `360a89e9c11afadd78720fc1bd77caea2cfb653c1e6e95694d05cd600ac2a202`

**Change:** After the hourly transaction attempt, the workflow now reads the contract's
`commitCount()`, refreshes `attest/onchain_ledger.json`, regenerates `attest/VERIFICATION.md`, and
copies the report into the demo bundle before pushing the public record.

**Why signal meaning is unchanged:** This is a read-only post-commit reporting step. It does not
change the strategy spec, signal computation, hash, salt, transaction timing, or contract call.
Failure to refresh the snapshot does not prevent the CSV/heartbeat push.

## 5. All other frozen-set files — byte-identical

The workflow still keeps `cancel-in-progress: false`; the existing single-flight and on-chain
duplicate guards remain unchanged.
Every other frozen file matches `frozen_set_baseline.txt` exactly. Verify:

    sha256sum -c evidence/frozen_set_baseline.txt   # 10 OK; three approved changes are logged above
