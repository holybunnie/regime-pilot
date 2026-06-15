> ⚠️ **Internal working doc — remove before final submission.** Not judge-facing. The README +
> STATUS are the canonical, self-contained documents; this file must never contradict them.

# HANDOFF — continuation guide

Working state for continuing the Regime Pilot build (BNB Hack Track 2). The operator
(holybunnie) reviews via plain-English reports and PASS/FAIL scripts — verify everything with
scripts, report in plain English.

## What this is
A CoinMarketCap Strategy Skill: a natural-language→spec compiler, a deterministic
lookahead-proof backtest engine, a flagship regime-routing strategy, a falsification battery,
and an on-chain commit-reveal attestation on BSC mainnet. The contribution is the **honest,
tamper-evident measurement system**; the strategy is the test subject.
Repo: https://github.com/holybunnie/regime-pilot · Freeze: **2026-06-21 13:00 UTC**.

## 🔴 NON-NEGOTIABLE RULES
- **Commits:** author `holybunnie` only; clean conventional messages; no co-author or "generated"
  trailers of any kind; no authoring-tool name in messages, files, or collaborators. No build-order
  scaffolding language in judge-facing files.
- **Push:** use the PAT in `.env` as `GH_PAT`. Always `git pull --rebase` BEFORE every push — the
  hourly cron pushes to main. Never print or commit `GH_PAT` or any `.env` value; scan the staged
  diff for secret values first.
- **Mainnet for the live record.** Contract `0xB87481e29b0Dce9545b1B00b8526810679B521c1` (BSC).
  Wallet `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`. Testnet is used ONLY for the Item-3 reveal
  rehearsal (operator-approved) and never for the attested forward record.
- **ATTESTATION FREEZE (the FROZEN SET):** the hourly cron computes signals from the frozen specs.
  Do NOT change the *meaning* of `spec/regime_pilot.spec.json`, `spec/regime_pilot_v2.spec.json`,
  `spec/universe.json`, or the signal path (`compute_signal`, `build_features`, `assign_regimes`,
  `target_weights`, `indicators.py`, `sizing.py`, `hashing.py`, `engine/data/fetch.py`). Baseline
  hashes: `evidence/frozen_set_baseline.txt`; approved exceptions logged in
  `evidence/frozen_set_changes.md`. The only approved change is the duplicate-guard added to
  `attest/commit_hour.py` (skip-logic only; signal/hash bytes unchanged). After ANY engine edit
  run `python tests/test_engine.py` and `PYTHONPATH=. python attest/verify.py` — the latter MUST
  still account for every on-chain commit.

## Status: DONE (offline `make verify` passes top to bottom)
All components are built, tested, and committed — consistent with STATUS.md:
- Environment / credentials — DONE (live gate: `make verify-environment`)
- Data layer — DONE (live gate: `make verify-data`)
- Spec schema — DONE (`make verify-spec`)
- Skill (compiler) — DONE (`make verify-skill`)
- Backtest engine (deterministic + no-lookahead) — DONE (`make verify-engine`)
- Flagship strategy (v1 + v2) — DONE (live gate: `make verify-strategy`)
- Falsification battery — DONE (`make verify-falsification`)
- On-chain attestation — LIVE; every commit accounted for (`make attest-verify`)
- Duplicate-commit guard — DONE (`make verify-attest-race`)
- x402 data plan — DONE (`make verify-x402`)
- Secret-leak gate — DONE (`make verify-secrets`)
- Verify harness — DONE (`make verify` offline scoreboard; `make verify-full` live)

## Attestation — LIVE, hands-off
- The attested strategy is **v2** (long/short). v1 stays verifiable. The committer is
  `attest/commit_hour.py`, run hourly by `.github/workflows/attest.yml`. Repo secrets:
  `CMC_API_KEY`, `ATTEST_PRIVATE_KEY`, `ATTEST_SALT_SEED`.
- Salt is deterministic `keccak(ATTEST_SALT_SEED || timestamp)` so reveals are reproducible.
- The chain holds 34 commits; ids 7 and 26 are documented exact-duplicates (see
  `attest/RECONCILIATION.md`), and the duplicate-race is now closed (single-flight lock +
  on-chain pre-send guard in `attest/single_flight.py`).
- `make attest-status` (liveness) · `make attest-verify` (chain-complete accounting, offline-capable
  from `attest/onchain_ledger.json`).

## Reveal day (June 20–21)
`make attest-reveal` writes `reveals.json` / `revealed_payloads.json` (force-add the public one —
it's gitignored pre-reveal); add `--onchain` to also call `reveal()` on BSC. Then `make
attest-verify` recomputes every on-chain hash from the revealed payloads → `attest/VERIFICATION.md`.
This procedure is already rehearsed end-to-end against a real in-memory EVM
(`attest/REVEAL_DRYRUN.md`), so reveal day is a replay.

## Key commands
`make verify` (offline) · `make verify-full` (live) · the claim-based `make verify-*` gates ·
`make data` · `make backtest` · `make falsify` · `make attest-status|attest-commit|attest-verify|attest-reveal`.
Run engine/attest scripts with `PYTHONPATH=.`. Python 3.12; deps in `requirements.txt`.
