# AGENTS.md — guide for any engineer or agent auditing / continuing this repo

This file lets a fresh agent (or human auditor) understand exactly what exists, verify every
claim independently, and continue the work without breaking the live system. Read it fully before
acting. The operator reviews via plain-English reports and PASS/FAIL scripts.

## 1. What this is (one paragraph)
**Regime Pilot** is a CoinMarketCap "Strategy Skill" (BNB Hack Track 2). It compiles natural-language
trading intent into a strict JSON **strategy spec** (closed predicate AST, no code), executes it in a
**deterministic, lookahead-proof backtest engine**, runs a **falsification battery** against it, and
**notarizes its live hourly signals on BNB Smart Chain** via commit-reveal so the forward test cannot
be curve-fit. It also includes an **x402** data-cost analysis with one real on-chain micro-payment.
An LLM appears in exactly one place — authoring the spec — and never touches execution or results.

## 2. One-command audit
```bash
make setup && make data && make verify
```
`make verify` runs every phase gate and prints a PASS/FAIL scoreboard. Expected: all PASS.
Individual gates: `make verify-phase{0,1,3,4,5,6,7,8,9}` (and `make falsify` regenerates Phase 6).

## 3. Claim → evidence map (how to verify each headline)
| Claim | Where | How to verify independently |
|------|-------|------------------------------|
| Specs are safe/closed-grammar; bad specs rejected | `spec/schema.json`, `cli/validate_spec.py` | `make verify-phase2` (8 malformed specs rejected) |
| Backtest is deterministic | `engine/backtest.py` | `make verify-phase4` → "byte-identical" test runs the same spec twice |
| No lookahead | `engine/backtest.py` (`GuardedAccessor` + 1-hour feature shift) | `make verify-phase4` → guard rejects future/at-T reads; feature[T] uses data ≤ T-1 |
| Sizing law + de-risk ladder correct | `engine/sizing.py` | `make verify-phase4` → ladder boundary tests (incl. the float-epsilon edge) |
| Data integrity | `engine/data/`, `cli/verify_phase1.py` | `make verify-phase1` → no gaps/dupes, UTC, live Binance spot-check |
| Strategy results honest | `engine/reports/*/report.md`, `falsify/REPORT*.md` | `make falsify`; deflated Sharpe ≈ 0.01 (no overstated edge); shuffle canary passes |
| Skill is installable + LLM quarantined | `skill/SKILL.md`, `skill/compiler_prompt.md`, `skill/examples/` | `make verify-phase3` (CMC frontmatter, 3 intents incl. refusal, downstream byte-identical) |
| On-chain attestation real | `attest/`, contract on BSC | see §4 — verify a commit yourself |
| x402 real payment | `x402plan/`, `evidence/x402_executed_payment.json` | balance 1.5000→1.4900 USDC, HTTP 200, settled; `make verify-phase8` |
| Repo is secret-free | `cli/verify_phase9.py` | `make verify-phase9` greps tracked files + full git history |

## 4. Auditing the on-chain attestation (the differentiator)
- Contract (BSC mainnet): **0xB87481e29b0Dce9545b1B00b8526810679B521c1**
  (https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1)
- Hash recipe: `commit_hash = keccak256( canonical_json(signal) || salt )`,
  `salt = keccak256( ATTEST_SALT_SEED || timestamp_utc )`. Signal =
  `{spec_version, spec_hash, universe_hash, timestamp_utc, regime, target_weights}`.
- `make attest-verify` recomputes every commit's hash from public data + the frozen spec and checks
  it against the chain, and checks the block timestamp predates the signal's outcome ("prompt").
  It auto-selects, per commit, whichever spec (v1 or v2) reproduces the on-chain hash.
- Honest record: commit id=0 is a manual bootstrap committed late (flagged not-prompt ⚠️); one early
  hour is logged as MISSED (the env-var bug, since fixed). Gaps/misses are recorded, never hidden.
- Scheduling: GitHub's native cron is unreliable for new repos, so an external pinger (cron-job.org)
  POSTs the `workflow_dispatch` API hourly; `.github/workflows/attest.yml` runs `attest/commit_hour.py`.

## 5. Honest limitations (an auditor should know these up front)
- **No statistically significant edge.** Over the bear-market backtest window, deflated Sharpe ≈ 0.01
  for both v1 and v2. The value proposition is capital preservation + the *verifiable forward test*,
  not a proven alpha. This is stated everywhere; do not "fix" it by tuning (that inflates trials and
  the deflated-Sharpe bar — and the shuffle canary/forward record would expose it).
- **Hybrid data.** Backtest prices = Binance public hourly OHLCV (the operator's CMC tier blocks price
  history); sentiment = CMC Fear & Greed; live attestation signals = CMC. Documented in `DECISIONS.md`.
- **Interim universe.** 15 liquid majors pending the brief's official 149-token list (engine is
  universe-agnostic; replace `spec/universe.json` and re-run `make data`).
- **Ranking** by 24h dollar-volume (market-cap history not on the free tier).
- **Not yet done:** BscScan source verification (needs `BSCSCAN_API_KEY`); the reveal step (June 20–21).

## 6. Architecture / data flow
intent → `skill/` (LLM authors spec) → `spec/*.spec.json` → `engine/` (deterministic backtest)
→ `falsify/` (walk-forward, perturbation, shuffle canary, deflated Sharpe, ablation)
→ frozen spec → `attest/commit_hour.py` (hourly) → `SignalAttestor.sol` on BSC → reveal + verify.
`x402plan/` prices the data feeds. `evidence/` holds raw API/tx proofs. `cli/` holds the gates.

## 7. 🔴 Operational rules (do not break the live system)
- **Commits:** author `holybunnie` only; clean conventional messages; **no** co-author / "generated"
  trailers; **no** "Phase N" in messages; keep any authoring-tool name out of messages/files.
- **Push:** PAT is in `.env` as `GH_PAT` (Codespaces token can't push). ALWAYS `git pull --rebase`
  (with the PAT URL) before pushing — the hourly cron also pushes to main. Never print/commit `GH_PAT`
  or any `.env` value; scan the staged diff for secret values first.
- **Mainnet only**, never testnet. Wallet `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`.
- **FROZEN — do not change behavior of:** `spec/regime_pilot.spec.json`,
  `spec/regime_pilot_v2.spec.json`, `spec/universe.json`, and the engine signal path
  (`compute_signal`, `build_features`, `assign_regimes`, `target_weights`, `indicators.py`,
  `sizing.py`). Changing them breaks re-verification of past on-chain commits. New work must be
  ADDITIVE. After any engine edit run `make verify-phase4 && make verify-phase5` and
  `PYTHONPATH=. python attest/verify.py` (the last MUST still show all on-chain hashes match).

## 8. Environment
Python 3.12; deps in `requirements.txt`. solc 0.8.24 lives at `~/.solcx` (fetched from GitHub
releases — the default solc host is DNS-blocked in this sandbox). Run engine/attest scripts with
`PYTHONPATH=.`. The cron's GitHub Actions secrets: `CMC_API_KEY`, `ATTEST_PRIVATE_KEY`,
`ATTEST_SALT_SEED`.
