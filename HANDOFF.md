# HANDOFF — continuation guide

Working state for continuing the Regime Pilot build (BNB Hack Track 2). The operator
(holybunnie) reviews via plain-English reports and PASS/FAIL scripts — verify everything
with scripts, report in plain English.

## What this is
A CoinMarketCap Strategy Skill: a natural-language→spec compiler, a deterministic
lookahead-proof backtest engine, a flagship regime-routing strategy, a falsification report,
and an on-chain commit-reveal attestation on BSC mainnet.
Repo: https://github.com/holybunnie/regime-pilot · Freeze: **2026-06-21 13:00 UTC**.

## 🔴 NON-NEGOTIABLE RULES
- **Commits:** author `holybunnie` only; clean conventional messages; no co-author or "generated"
  trailers of any kind; no "Phase N" in messages; keep the word/name of any authoring tool out of
  messages, files, and collaborators. Git is configured for this.
- **Push:** use the PAT in `.env` as `GH_PAT` (the Codespaces token can't push). Always
  `git pull --rebase` (with the PAT URL) BEFORE every push — the hourly cron pushes to main:
  `git push "https://x-access-token:${GH_PAT}@github.com/holybunnie/regime-pilot.git" main:main`
  Never print or commit `GH_PAT` or any `.env` value; scan the staged diff for secret values first.
- **Mainnet only** — never testnet. Contract `0xB87481e29b0Dce9545b1B00b8526810679B521c1` (BSC).
  Wallet `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`.
- **ATTESTATION FREEZE:** the hourly cron computes/recomputes signals from the frozen specs.
  Do NOT change behavior of `spec/regime_pilot.spec.json`, `spec/regime_pilot_v2.spec.json`,
  `spec/universe.json`, or the engine signal path (`compute_signal`, `build_features`,
  `assign_regimes`, `target_weights`, `indicators.py`, `sizing.py`). Changes must be ADDITIVE.
  After ANY engine edit run `python tests/test_engine.py`, `python cli/verify_phase5.py`, and
  `PYTHONPATH=. python attest/verify.py` — the last MUST still show all on-chain hashes match.

## Status: done (all gates pass)
Phases 0 (discovery), 1 (data: Binance hourly OHLCV + CMC Fear&Greed; 15-token INTERIM universe —
official 149-list still pending), 2 (schema), 3 (the Skill), 4 (engine: deterministic + no
lookahead), 5 (flagship v1 long-only + v2 long/short), 6 (falsification), 7 (attestation LIVE).
`make verify` runs the full scoreboard; `make verify-phase{0,1,2,3,4,5,6,7}` individually.

## Attestation (Phase 7) — LIVE, hands-off
- The strategy attested forward is **v2** (long/short). v1 stays verifiable; to revert, repoint
  `attest/commit_hour.py` SPEC back to `regime_pilot.spec.json`.
- **Scheduling:** GitHub's own cron is unreliable for new repos (best-effort, delayed/skipped), so
  an external free pinger (cron-job.org) POSTs to the workflow_dispatch API hourly. The workflow
  `.github/workflows/attest.yml` runs `attest/commit_hour.py`. Repo secrets: CMC_API_KEY,
  ATTEST_PRIVATE_KEY, ATTEST_SALT_SEED.
- Records: `attest/commits_public.csv` (public) + `attest/log.jsonl` (private, gitignored).
  Salt is deterministic `keccak(ATTEST_SALT_SEED || timestamp)` so reveals are reproducible.
- `make attest-status` (liveness) · `make attest-verify` (recompute + check all on-chain hashes;
  it matches each commit to whichever spec reproduces its hash, handling the v1→v2 switch).

## NOT STARTED
- **Phase 8 — x402 data plan.** Probe CMC x402 (endpoints in `evidence/x402_endpoints.md`;
  $0.01 USDC/request on Base). Execute ≥1 REAL paid request (wallet holds ~1.5 USDC on Base; x402
  is gasless EIP-3009 — verify). Output `x402plan/DATA_PLAN.md`: per-feed weekly cost, KEEP/DROP
  from the ablation, flagship return net of data costs. `make verify-phase8` recomputes from JSON.
- **Phase 9 — README + demo.** Judge-facing README (contract link, how to verify one commit in
  60s, quickstart, honest limitations). `make demo` regenerates charts offline <5min.
  `make verify-phase9` greps repo + history for secrets.
- **Phase 10** — extend the `make verify` scoreboard as phases land. Also: verify the contract
  source on BscScan (needs `BSCSCAN_API_KEY`).

## Key commands
`make verify` (full) · `make verify-phaseN` · `make data` · `make backtest` · `make falsify` ·
`make attest-status|attest-commit|attest-verify|attest-reveal`.
Run engine/attest scripts with `PYTHONPATH=.`. Python 3.12; deps in requirements.txt; solc 0.8.24
at `~/.solcx` (fetched from GitHub releases — the default solc host is DNS-blocked in this sandbox).

## Reveal day (June 20–21)
`make attest-reveal` writes `reveals.json` / `revealed_payloads.json` (force-add the public one
then — it's gitignored pre-reveal); add `--onchain` to also call `reveal()` on BSC. Then
`make attest-verify` produces `attest/VERIFICATION.md` (table + forward equity from committed
signals).
