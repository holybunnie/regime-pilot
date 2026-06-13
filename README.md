# Regime Pilot — a CoinMarketCap Strategy Skill (BNB Hack Track 2)

Turn a plain-English trading idea into a **deterministic, machine-checkable strategy spec**,
backtest it with **no lookahead and no hidden randomness**, try hard to **disprove** its own edge,
and **notarize its live hourly signals on BNB Smart Chain** via commit-reveal — so the forward
test provably cannot be curve-fit after the fact.

> **The LLM only authors the spec; it never touches execution or results.** Everything downstream
> of the spec file is pure, deterministic Python. That separation is the whole point.

**Live contract (BSC mainnet):** [`0xB87481e29b0Dce9545b1B00b8526810679B521c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1)
· **Repo:** https://github.com/holybunnie/regime-pilot

---

## Architecture

```
 plain-English intent
        │   skill/ (the CMC Strategy Skill — the ONLY LLM in the system)
        ▼
   strategy spec (JSON, schema-validated, closed predicate AST)   spec/
        │
        ▼
 deterministic backtest engine  ───────────────►  falsification report      falsify/
   engine/ (no-lookahead, byte-identical)          (walk-forward, perturbation,
        │                                            shuffle canary, deflated
        │                                            Sharpe, ablation)
        ▼
 frozen spec ─► hourly committer ─► SignalAttestor.sol on BSC (commit-reveal)   attest/
        │            (GitHub Actions cron, hourly)        │
        └──────────► reveal + independent verification ◄──┘
                                                          │
                          x402 data-cost plan  ◄──────────┘   x402plan/
                          (real $0.01 USDC paid on Base)
```

## Quickstart (≤ 3 commands)

```bash
make setup        # install pinned deps (Python 3.12)
make data         # fetch ~13 months hourly data into a local cache (~2 min)
make backtest && make falsify
```
Then `make verify` prints the full PASS/FAIL scoreboard.

## The differentiator: provable, un-fakeable forward testing

Every hour, a GitHub Actions cron computes the frozen strategy's signal from public data **and
commits a hash of it on-chain before that hour's outcome is known**:

```
commit_hash = keccak256( canonical_json(signal) || salt )      # signal = {spec_hash, universe_hash, timestamp, regime, target_weights}
salt        = keccak256( secret_seed || timestamp )            # deterministic → reproducible at reveal
```

**Verify any commit yourself in ~60 seconds:**
1. Open the contract on BscScan (link above) → read `getCommit(id)` for the on-chain hash + block timestamp.
2. Take the revealed signal + salt (published at reveal) and recompute `keccak256(canonical_json || salt)`.
3. It matches the on-chain hash, and the block timestamp predates the market outcome → the signal
   could not have been fitted after the fact.

`make attest-verify` does this for **every** commit and writes `attest/VERIFICATION.md`. The
verifier auto-matches each commit to the exact spec version that produced it.

## Falsification highlights (honest)

Run `make falsify`; see `falsify/REPORT.md` (v1) and `falsify/REPORT_regime_pilot_v2.spec.md` (v2).
The backtest window was a **bear market (BTC −45%)**.

- **Capital preservation:** the long-only v1 returned −10.4% (vs BTC −45%); the long/short v2
  improved risk-adjusted and out-of-sample results (embargo +1.8%, Sharpe ~3.0).
- **Shuffle canary: passed** — the edge vanishes on time-shuffled data, so there's no lookahead/leakage.
- **Robust** to ±20% parameter perturbation.
- **Deflated Sharpe ≈ 0.01** — stated plainly: neither version has a *statistically significant*
  directional edge over the bear window. We do **not** overstate; the live forward test is the arbiter.

## x402 data-cost plan (real payment)

`x402plan/DATA_PLAN.md`. We executed **one real $0.01 USDC x402 payment on Base** (gasless,
EIP-3009, settled — wallet 1.5000 → 1.4900 USDC; evidence in `evidence/`). The plan recomputes
per-feed weekly cost, the minimal viable feed set, net-of-cost out-of-sample return, and the
break-even capital (~$400) below which the free data sources win.

## What runs where (and honest limitations)

- **Backtest prices:** Binance public hourly OHLCV (the operator's CMC tier blocks price history —
  documented in `DECISIONS.md`). **Sentiment:** CMC Fear & Greed history. **Live signals:** CMC.
- **Universe:** an interim set of 15 liquid majors pending the brief's official 149-token list
  (the engine is universe-agnostic; drop the list into `spec/universe.json`).
- **Asset ranking** uses 24h dollar-volume (market-cap history isn't on the free tier).
- This project executes **zero trades**; all timestamps are UTC. **Backtested and attested-forward
  performance does not predict future results.**

## Layout
`skill/` the Skill · `spec/` schema + strategies · `engine/` deterministic backtester ·
`falsify/` falsification · `attest/` on-chain · `x402plan/` data costs · `evidence/` raw API
proofs · `cli/` verifiers · `STATUS.md` / `DECISIONS.md` / `ASSUMPTIONS.md` plain-English logs.
