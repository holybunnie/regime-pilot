# Phase 7 — On-Chain Attestation (BSC mainnet) Evidence

Deployed 2026-06-13 ~08:20 UTC.

## Contract
- **SignalAttestor** (commit-reveal notary, MIT, no funds, no external calls, not upgradeable)
- Address: **0xB87481e29b0Dce9545b1B00b8526810679B521c1**
- BscScan: https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1
- Deploy tx: 0x8c73ac0e9f0ca45921b52ed142bb787c8d82d80c567829d1c9fc798c02280d75
- Owner / committer: 0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1
- Chain: BSC mainnet (56). Deploy gas used: 310,958 (~0.000043 BNB at 0.11 Gwei).
- Solidity 0.8.24 (compiler downloaded from GitHub releases; default host blocked in sandbox).

## Hash recipe (verifiable)
`commit_hash = keccak256( canonical_json(payload) || salt )`
- canonical_json = sorted keys, no whitespace, UTF-8
- salt = keccak256( secret_seed || timestamp_utc )  (deterministic → reproducible at reveal)
- payload = { spec_version, spec_hash, universe_hash, timestamp_utc, regime, target_weights }
- Known-answer locked in tests/test_attest.py:
  payload {regime:chop,spec_version:1.0.0,timestamp_utc:2026-06-13T08:00:00Z} + salt 0x..01
  → 0x7afc73b86475e098f34b1cc785196adcbb5277c37a5f9a4c99c86f76afe5146b

## First commits
| id | effective hour | regime | tx | note |
|---:|----------------|--------|----|------|
| 0 | 2026-06-13T07:00:00Z | chop | 0x82f56c98… | bootstrap (committed ~83 min late → flagged not-prompt) |
| 1 | 2026-06-13T08:00:00Z | chop | 0x60be1b0c… | proper forward commit (prompt ✅) |

Both hashes independently reproduced from public data (verify.py): 2/2 match.

## Why this proves no curve-fitting
Each hour we publish a hash of the signal BEFORE the outcome of that hour is known (the
GitHub Actions cron runs at HH:05 and commits the signal effective for [HH:00, HH+1:00)).
The block timestamp is immutable. At reveal, anyone recomputes the signal from the frozen
spec + public market data + published salt and checks it equals the on-chain hash and that
the block time predates the outcome. A forward track record that matches pre-committed
hashes cannot have been fitted after the fact.
