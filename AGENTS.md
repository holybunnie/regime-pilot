# AGENTS.md — guide for any engineer or agent auditing / continuing this repo

This file lets a fresh agent (or human auditor) understand exactly what exists, verify every
claim independently, and continue the work without breaking the live system. Read it fully before
acting. The operator reviews via plain-English reports and PASS/FAIL scripts.

> **Pickup note (pre-submission hardening, branch `fixes/pre-submission`):** a hardening pass is
> in progress. See **§9 — Resume here** for exactly what is done and what remains.

## 1. What this is (one paragraph)
**Regime Pilot** is an **honest, tamper-evident measurement system for AI-authored trading
strategies** (CoinMarketCap Strategy Skill, BNB Hack Track 2). It compiles natural-language intent
into a strict JSON **strategy spec** (closed predicate AST, no code), executes it in a
**deterministic, lookahead-proof backtest engine**, runs a **falsification battery** against it, and
**notarizes its live hourly signals on BNB Smart Chain** via commit-reveal so the forward test cannot
be curve-fit. It includes an **x402** data-cost analysis with one real on-chain micro-payment. An LLM
appears in exactly one place — authoring the spec — and never touches execution or results. **The
contribution is the trustworthy measurement; the strategy is the test subject** (it has no
statistically significant edge, stated plainly).

## 2. One-command audit
```bash
make setup && make verify        # OFFLINE — no secrets, no network, no downloaded data
make verify-full                 # adds live checks (needs CMC key + make data)
```
`make verify` prints a single PASS/FAIL scoreboard, one line per submission item. Expected: all
PASS (13 offline gates). Claim-based individual gates are listed by `make help`.

## 3. Claim → evidence map (how to verify each headline)
| Claim | Where | How to verify independently |
|------|-------|------------------------------|
| Specs are safe/closed-grammar; bad specs rejected | `spec/schema.json`, `cli/validate_spec.py` | `make verify-spec` |
| Backtest deterministic + no-lookahead + sizing | `engine/backtest.py`, `engine/sizing.py` | `make verify-engine` (offline, uses committed fixture) |
| Data integrity | `engine/data/`, `cli/verify_phase1.py` | `make verify-data` (live) |
| Strategy results honest | `engine/reports/*`, `falsify/REPORT*` | `make verify-falsification`; deflated Sharpe ≈ 0.01; shuffle canary passes |
| Skill installable + LLM quarantined | `skill/` | `make verify-skill` (live/data) |
| Every on-chain commit accounted for | `attest/verify.py`, `attest/onchain_ledger.json` | `make attest-verify` (offline-capable; iterates `commitCount()`) |
| Duplicate-commit race closed | `attest/single_flight.py` | `make verify-attest-race` |
| Reveal works end-to-end | `attest/dryrun_reveal.py`, `attest/REVEAL_DRYRUN.md` | `PYTHONPATH=. python attest/dryrun_reveal.py` (real in-memory EVM) |
| x402 real payment | `x402plan/`, `evidence/x402_executed_payment.json` | `make verify-x402` |
| Repo secret-free | `cli/verify_phase9.py` | `make verify-secrets` (tracked files + full git history) |
| Data sources/credentials mapped to real call sites | `DATA_SOURCES.md` | `make verify-datasources` |
| Framing honest; README self-contained | `README.md`, `STATUS.md` | `make verify-framing`, `make verify-readme` |
| 149-token universe ready; CMC Pro optional | `spec/universe_official_149.json`, `engine/datasource.py` | `make verify-universe`, `make verify-datasource` |

## 4. Auditing the on-chain attestation (the differentiator)
- Contract (BSC mainnet): **0xB87481e29b0Dce9545b1B00b8526810679B521c1**.
- Recipe: `commit_hash = keccak256(canonical_json(signal) || salt)`,
  `salt = keccak256(ATTEST_SALT_SEED || timestamp_utc)`.
- `make attest-verify` iterates the contract's own `commitCount()` and classifies EVERY on-chain id
  (RECORDED / REPRODUCED / DOCUMENTED-DUPLICATE). Pass = zero unaccounted. Works offline from the
  committed snapshot `attest/onchain_ledger.json`.
- **Honest record:** the chain grows by one commit per hour (live count in `onchain_ledger.json` /
  `VERIFICATION.md`); ids **7 and 26** are exact-duplicate commits (same hash, second hourly run for
  the same hour) — fully documented in `attest/RECONCILIATION.md`; the race that caused them is
  closed. One early hour logged MISSED (since fixed). Nothing hidden.

## 5. Honest limitations
- **No statistically significant edge** (deflated Sharpe ≈ 0.01 both versions). Do NOT "fix" by
  tuning — that inflates trials and the shuffle canary/forward record would expose it.
- **Hybrid data:** backtest prices = Binance public OHLCV; sentiment + live signal = CMC. CMC Pro is
  a wired-but-optional upgrade (`engine/datasource.py`, `DATA_PLAN.md`). Full map: `DATA_SOURCES.md`.
- **Interim 15-token universe** pending the official 149-list (`spec/universe_official_149.json` ready).
- **Ranking** by 24h dollar-volume. **Reveal** runs June 20–21 (rehearsed: `attest/REVEAL_DRYRUN.md`).

## 6. Architecture / data flow
intent → `skill/` (LLM authors spec) → `spec/*.spec.json` → `engine/` (deterministic backtest)
→ `falsify/` → frozen spec → `attest/commit_hour.py` (hourly) → `SignalAttestor.sol` on BSC →
reveal + verify. `x402plan/` prices feeds. `evidence/` holds proofs + the frozen-set baseline.

## 7. 🔴 Operational rules (do not break the live system)
- **Commits:** author `holybunnie` only; clean messages; **no** co-author / "generated" trailers;
  **no** build-order/"phase N" scaffolding or authoring-tool names in judge-facing files.
- **Push:** PAT in `.env` as `GH_PAT`. ALWAYS `git pull --rebase` before pushing — the hourly cron
  also pushes to main. Never print/commit `GH_PAT` or any `.env` value; scan the staged diff first.
- **Mainnet for the live record.** Wallet `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`. Testnet/
  in-memory EVM is used ONLY for the reveal rehearsal — never the attested record.
- **FROZEN SET — do not change the *meaning* of:** `spec/regime_pilot.spec.json`,
  `spec/regime_pilot_v2.spec.json`, `spec/universe.json`, `attest/{commit_hour,chain,hashing,
  live_signal}.py`, `engine/{backtest,sizing,indicators}.py`, `engine/data/fetch.py`,
  `attest/deployment.json`, `.github/workflows/attest.yml`. Baseline: `evidence/frozen_set_baseline.txt`;
  approved exceptions: `evidence/frozen_set_changes.md` (only the duplicate-guard added to
  `commit_hour.py`, skip-logic only). After any change run `make verify` and
  `PYTHONPATH=. python attest/verify.py`.

## 8. Environment
Python 3.12; deps in `requirements.txt` (incl. `eth-tester[py-evm]`, `pytest`). solc 0.8.24 at
`~/.solcx`. Run engine/attest scripts with `PYTHONPATH=.`. Cron GitHub Actions secrets:
`CMC_API_KEY`, `ATTEST_PRIVATE_KEY`, `ATTEST_SALT_SEED`.

## 9. Resume here — pre-submission hardening status (branch `fixes/pre-submission`)
**DONE and verified (each has a runnable gate; `make verify` = 13/13 PASS offline):**
- Item 1 — reconciled on-chain commits 7 & 26 (documented duplicates); chain-complete `attest/verify.py`
  (+ `onchain_ledger.json`, `RECONCILIATION.md`, `commits_reconciliation.csv`).
- Item 2 — duplicate-commit race closed: `attest/single_flight.py` (lock + on-chain pre-send guard),
  wired into `commit_hour.py` (operator-approved, signal/hash bytes unchanged), `make verify-attest-race`.
- Item 4/7 — honest framing (full-window first; "no statistically significant"; precise timing) +
  `make verify-framing`. Item 9/10 — README rewritten system-first, Binance own-goal removed,
  `make verify-readme`.
- Item 5 — `make verify` is now an OFFLINE scoreboard (`cli/verify.py`) using committed fixtures
  (`tests/fixtures/cache_csv/`, builder `cli/build_fixtures.py`).
- Item 6 — `eth-tester[py-evm]` + `pytest` pinned; `tests/test_attest.py` runs; `.github/workflows/ci.yml` added.
- Item 8 — `spec/universe_official_149.json` (149 tokens) + `make verify-universe`.
- Item 11 — `engine/datasource.py` (CMC Pro optional) + `DATA_PLAN.md` + `make verify-datasource`.
- Item 12 — HANDOFF aligned with STATUS + `make verify-docs-consistency`.
- Item 13 — `make verify-secrets` (files + full git history).
- Item 14 — Makefile targets renamed to claim-based names; zero `phase[0-9]` in judge-facing files.
- Item 15 — `DATA_SOURCES.md` (code-verified) + `make verify-datasources`.
- Item 3 — reveal rehearsal: `attest/dryrun_reveal.py` + `make attest-dryrun-verify` (5/5 reproduce on
  the real compiled contract via in-memory EVM). Public BSC-testnet tx links intentionally skipped
  (operator decision) — the script is identical with a funded testnet key.
- SELF_AUDIT — `SELF_AUDIT.md` (10 hostile questions, answers, residual risks) + `make verify-self-audit`.
- CI — confirmed green on GitHub (`.github/workflows/ci.yml`: setup, offline scoreboard, attest unit
  test, race guard).
- Ledger drift fix — `attest/snapshot_ledger.py` + `make attest-snapshot` regenerate the offline
  snapshot from the chain's own `commitCount()` (read-only); `make attest-verify` passes online AND
  offline. Commit-count claims in the docs no longer pin a fixed number the hourly committer outgrows.
- Final gate — fresh-clone `make setup && make verify` = 13/13; FROZEN SET = 12 byte-identical +
  `commit_hour.py` (approved). Done.

**REMAINING (optional):**
1. **Verify-full cold path** — confirm `make verify-full` behaves on a machine with a CMC key + `make data`.
2. **Secret scan deepening** — extend the scan with explicit salt-seed/key regexes if desired.
3. At submission: strip this file, HANDOFF.md, and any scaffolding (operator's call).
7. At submission: strip this file, HANDOFF.md, and any scaffolding (operator's call).
