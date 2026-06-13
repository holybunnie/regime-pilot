# CLAUDE.md — handoff / continuation guide

Read this first. It's the working state for continuing the Regime Pilot build
(BNB Hack Track 2). Operator (holybunnie) cannot read code — report in plain English,
verify everything with scripts.

## What this is
A CoinMarketCap Strategy Skill: NL→spec compiler, deterministic lookahead-proof backtest
engine, a flagship regime-routing strategy, a falsification report, and an on-chain
commit-reveal attestation on BSC mainnet. Repo: https://github.com/holybunnie/regime-pilot
Freeze (submission): **2026-06-21 13:00 UTC**.

## 🔴 NON-NEGOTIABLE RULES (also in memory/)
- **Commits:** author `holybunnie`, NO AI attribution, NO "Phase N" in messages, clean conventional messages. Git already configured.
- **Push:** use the PAT in `.env` as `GH_PAT`. The Codespaces token can't push. Pattern:
  `git pull --rebase` (with the PAT URL) BEFORE every push — the hourly cron pushes to main.
  `git push "https://x-access-token:${GH_PAT}@github.com/holybunnie/regime-pilot.git" main:main`
  Never print/commit GH_PAT or any .env value. Scan staged diff for secret values before committing.
- **Mainnet only** — never testnet. Contract: `0xB87481e29b0Dce9545b1B00b8526810679B521c1` (BSC).
  Wallet `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1` (~0.009 BNB + 1.5 USDC on Base).
- **ATTESTATION FREEZE:** the hourly cron computes/recomputes signals from the FROZEN v1 spec.
  Do NOT change behavior of: `spec/regime_pilot.spec.json`, `spec/universe.json`, or the engine
  signal path (`compute_signal`, `build_features`, `assign_regimes`, `target_weights`,
  `indicators.py`, `sizing.py`). Changes must be ADDITIVE (new optional params / new playbook
  actions v1 never uses). After ANY engine edit, run: `python tests/test_engine.py`,
  `python cli/verify_phase5.py`, and `PYTHONPATH=. python attest/verify.py` — the last MUST
  still show all on-chain hashes match.

## Status: phases done (all gates pass)
- 0 discovery, 1 data (Binance hourly OHLCV + CMC Fear&Greed; 15-token INTERIM universe — official
  149-list still pending from operator), 2 schema, 4 engine (deterministic + no-lookahead),
  5 flagship (v1: -10.4% vs BTC -45%, defensive), 6 falsification (shuffle PASS, robust, deflated
  Sharpe ~0.01 = honestly no proven edge over the bear window), 7 attestation LIVE.
- `make verify-phase0|1|2|4|5|6|7` all pass. `make verify` = full scoreboard.

## Attestation (Phase 7) — LIVE, hands-off
- GitHub Actions `.github/workflows/attest.yml` runs hourly at HH:05. Secrets set by operator:
  CMC_API_KEY, ATTEST_PRIVATE_KEY, ATTEST_SALT_SEED.
- Commits recorded in `attest/commits_public.csv` (public) + `attest/log.jsonl` (private, gitignored).
- `make attest-status` = one-line liveness. `make attest-verify` = recompute+check all on-chain hashes.
- Salt is deterministic: keccak(ATTEST_SALT_SEED || timestamp), so reveals are reproducible.

## DONE — v2 long/short re-froze the live attestation (2026-06-13)
v2 (`spec/regime_pilot_v2.spec.json`) adds disciplined shorting; tested better OOS without
overfitting (deflated Sharpe unchanged ~0.01 — no version has a *significant* edge over the bear
window; live forward test arbitrates). The cron now attests v2 (commit_hour SPEC -> v2). v1 file
is untouched; `attest/verify.py`/`reveal.py` match each commit to the spec that reproduces its
on-chain hash, so commits 0-3 (v1) + 4+ (v2) all verify. v1 is the fallback: to revert, repoint
`attest/commit_hour.py` SPEC back to regime_pilot.spec.json. v2 falsification:
`falsify/REPORT_regime_pilot_v2.spec.md`.

## (history) v2 shorting strategy build
Operator asked to make the bear-market edge significant WITHOUT p-hacking. The only honest lever:
let the strategy go SHORT in bear regimes (not just flat). Decision made: **if v2 genuinely tests
better out-of-sample, RE-FREEZE the live attestation to v2** (we're early, ~3 commits in).

Done so far (engine, ADDITIVE — v1 verified byte-identical, 3/3 commits still verify):
- `target_weights` has a new `short_assets` action → negative weights.
- run loop has optional `costs.short_borrow_bps_per_day` borrow cost (absent in v1 → no effect).

TODO for v2:
1. Write `spec/regime_pilot_v2.spec.json` (version 2.0.0): make `crowded_fragile` and/or a new
   bear regime use `action: short_assets` (short top-liquidity / low-breadth names); add
   `short_borrow_bps_per_day` (~e.g. 30) to costs; symmetric low-breadth short signal.
2. Backtest it (`python engine/backtest.py spec/regime_pilot_v2.spec.json engine/reports/v2`).
3. Run falsification on v2 (parametrize falsify/report.py SPEC, or copy). Check OOS embargo +
   deflated Sharpe. ONLY re-freeze if it genuinely clears/improves OOS — do NOT curve-fit.
4. If re-freezing: keep v1 file untouched (for commits 0-2). Add v2 file. Make `attest/verify.py`
   and `attest/commit_hour.py` spec-aware: select the spec per commit by matching the committed
   payload's `spec_hash` (try v1 then v2). Point commit_hour SPEC at v2. Confirm v1 commits 0-2
   AND new v2 commits both verify. Update GH workflow if needed (it just runs commit_hour.py).
5. Document the v1→v2 switch honestly in README.

## NOT STARTED
- **Phase 8 — x402 data plan.** Probe CMC x402 (endpoints in evidence/x402_endpoints.md;
  $0.01 USDC/request on Base). Execute >=1 REAL paid request (wallet has 1.5 USDC on Base; x402
  is gasless EIP-3009 — verify). Output `x402plan/DATA_PLAN.md`: per-feed weekly cost, KEEP/DROP
  from ablation, flagship return net of data costs. `make verify-phase8` recomputes from JSON.
- **Phase 9 — README + demo.** Judge-facing README (contract link, how to verify one commit in
  60s, quickstart `make setup && make backtest && make falsify`, honest limitations). `make demo`
  regenerates charts offline <5min. `make verify-phase9` greps repo+history for secrets.
- **Phase 3 — Skill polish.** `skill/SKILL.md` (match evidence/cmc_skill_*_SKILL.md frontmatter
  format), compiler_prompt.md, 3 example intents incl. an impossible one. Not built yet.
- **Phase 10 — `make verify` scoreboard** exists; extend as phases land.

## Key commands
`make verify` (full), `make verify-phaseN`, `make data`, `make backtest`, `make falsify`,
`make attest-status|attest-commit|attest-verify|attest-reveal`.
Run engine/attest scripts with `PYTHONPATH=.`. Python 3.12, deps in requirements.txt + solc 0.8.24
at ~/.solcx (downloaded from GitHub; solc-bin host is DNS-blocked here).

## Reveal day (June 20-21)
`make attest-reveal` writes reveals.json/revealed_payloads.json (force-add the public one then,
it's gitignored pre-reveal); `--onchain` also calls reveal() on BSC. Then `make attest-verify`
produces attest/VERIFICATION.md (table + forward equity from committed signals).
