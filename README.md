# Regime Pilot — a CoinMarketCap Strategy Skill (BNB Hack Track 2)

Turn a plain-English trading idea into a **deterministic, machine-checkable strategy spec**,
backtest it with **no lookahead and no hidden randomness**, try hard to **disprove** its own edge,
and **notarize its live hourly signals on BNB Smart Chain** via commit-reveal — so the forward
test provably cannot be curve-fit after the fact.

> **The LLM only authors the spec; it never touches execution or results.** Everything downstream
> of the spec file is pure, deterministic Python. That separation is the entire design.

| | |
|---|---|
| **Contract (BSC mainnet)** | [`0xB87481e29b0Dce9545b1B00b8526810679B521c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1) |
| **Repo** | https://github.com/holybunnie/regime-pilot |
| **One-command proof** | `make verify` (full PASS/FAIL scoreboard) |
| **For auditors** | see [`AGENTS.md`](AGENTS.md) |

---

## Architecture

```
 plain-English intent
        │   skill/   (the CMC Strategy Skill — the ONLY LLM in the system)
        ▼
   strategy spec (JSON, schema-validated, closed predicate AST)        spec/
        │
        ▼
 deterministic backtest engine  ───────────────►  falsification report         falsify/
   engine/  (no-lookahead, byte-identical)         (walk-forward, perturbation,
        │                                            shuffle canary, deflated
        │                                            Sharpe, ablation)
        ▼
 frozen spec ─► hourly committer ─► SignalAttestor.sol on BSC (commit-reveal)   attest/
        │            (cron, hourly)                       │
        └──────────► reveal + independent verification ◄──┘
                                                          │
                          x402 data-cost plan  ◄──────────┘                     x402plan/
                          (one real $0.01 USDC paid on Base)
```

## Quickstart (≤ 3 commands)

```bash
make setup                       # install pinned deps (Python 3.12)
make data                        # ~13 months hourly data into a local cache (~2 min)
make backtest && make falsify    # run the strategy + the falsification battery
```
Then `make verify` prints the full scoreboard.

## Verify every claim yourself

| Claim | Command |
|------|---------|
| Bad specs are rejected; good ones accepted | `make verify-phase2` |
| Backtest is **deterministic** (byte-identical reruns) | `make verify-phase4` |
| **No lookahead** (guard rejects future reads; features use data ≤ T-1) | `make verify-phase4` |
| Drawdown-budget sizing + de-risk ladder are correct | `make verify-phase4` |
| Data has no gaps/dupes and matches live Binance | `make verify-phase1` |
| The Skill is installable + the LLM is quarantined | `make verify-phase3` |
| Falsification is complete and the shuffle canary passes | `make verify-phase6` |
| Every on-chain commit reproduces from public data | `make attest-verify` |
| The x402 payment was real and the plan recomputes | `make verify-phase8` |
| The repo leaks no secrets (files **and** git history) | `make verify-phase9` |

## The differentiator: a forward test that can't be faked

Every hour a cron computes the frozen strategy's signal from public data and commits a **hash** of
it on-chain **before that hour's outcome is known**:

```
signal      = {spec_version, spec_hash, universe_hash, timestamp_utc, regime, target_weights}
commit_hash = keccak256( canonical_json(signal) || salt )
salt        = keccak256( ATTEST_SALT_SEED || timestamp_utc )   # deterministic → reproducible at reveal
```

**Audit one commit in ~60 seconds:** read `getCommit(id)` on BscScan for the on-chain hash + block
timestamp; recompute `keccak256(canonical_json(revealed_signal) || salt)`; confirm it matches and
that the block timestamp predates the outcome. `make attest-verify` does this for **every** commit
and writes `attest/VERIFICATION.md`, auto-matching each commit to the spec version that produced it.

## Strategy & falsification (honest)

The backtest window was a **bear market (BTC −45%)**. Two strategy versions exist:

- **v1 (long-only)** — defensive regime router; returned **−10.4%** (vs BTC −45%): capital preservation.
- **v2 (long/short, live)** — adds disciplined shorting (only *confirmed* downtrends — breadth
  breakdown **and** price below its 30-day trend **and** volatility not extreme; never fades euphoria
  or shorts into capitulation; realistic borrow cost). Better out-of-sample: embargo **+1.8%**, Sharpe ~3.0.

Falsification (`falsify/REPORT.md`, `falsify/REPORT_regime_pilot_v2.spec.md`):
- **Shuffle canary: passed** — edge vanishes on time-shuffled data ⇒ no lookahead/leakage.
- **Robust** to ±20% parameter perturbation.
- **Deflated Sharpe ≈ 0.01** — stated plainly: **neither version has a statistically significant
  directional edge** over this window. We do not overstate; the live forward test is the arbiter.

## x402 data-cost plan (real payment)

`x402plan/DATA_PLAN.md`. We executed **one real $0.01 USDC x402 payment on Base** (gasless EIP-3009,
settled — wallet 1.5000 → 1.4900 USDC, HTTP 200, data delivered; `evidence/x402_executed_payment.json`).
The plan recomputes per-feed weekly cost, the minimal viable feed set, net-of-cost out-of-sample
return, and the break-even capital (~$400) below which the free data sources win. x402 also unlocks
derivatives (funding/OI) that the free REST tier blocks — material for a future strategy version.

## Repo layout

| Path | Contents |
|------|----------|
| `skill/` | the installable CMC Strategy Skill: `SKILL.md`, `compiler_prompt.md`, example intents |
| `spec/` | `schema.json` (the spec contract) + `regime_pilot.spec.json` (v1) + `regime_pilot_v2.spec.json` (v2) + `universe.json` |
| `engine/` | deterministic backtester: `backtest.py`, `indicators.py`, `sizing.py`, `data/` fetch+cache |
| `falsify/` | falsification suite + reports + `deflated_sharpe.py` |
| `attest/` | `contracts/SignalAttestor.sol`, deploy/commit/reveal/verify, `commits_public.csv` |
| `x402plan/` | x402 client (`pay_x402.py`), `prices.json`, `DATA_PLAN.md` |
| `cli/` | per-phase verification gates |
| `tests/` | unit tests (schema fuzz, sizing, engine, attestation, deflated Sharpe) |
| `evidence/` | raw saved API responses + on-chain/payment proofs |
| `demo/` | offline-regenerable charts + report bundle + runbook (`make demo`) |
| `STATUS.md` / `DECISIONS.md` / `ASSUMPTIONS.md` | plain-English logs |

## Honest limitations
- Hybrid data (Binance prices + CMC sentiment/live) — see `DECISIONS.md`.
- Interim 15-token universe pending the brief's official 149-token list (engine is universe-agnostic).
- Ranking by 24h dollar-volume (market-cap history not on the free tier).
- This project executes **zero trades**; all timestamps are UTC.
- **Backtested and attested-forward performance does not predict future results.**

## Status & reveal
See `STATUS.md` for the live scoreboard. The reveal (`make attest-reveal`) runs **June 20–21**,
after the forward record accumulates; it publishes payloads+salts and writes `attest/VERIFICATION.md`.
Contract source verification on BscScan is pending a `BSCSCAN_API_KEY`.
