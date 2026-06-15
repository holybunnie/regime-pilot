w# Regime Pilot — an honest, tamper-evident measurement system for AI-authored trading strategies

**Regime Pilot is a system that produces an honest, tamper-evident measurement of any
AI-authored trading strategy's edge** — a deterministic, lookahead-free backtest, a
falsification battery that actively tries to *disprove* the edge, and an on-chain
commit-reveal record that proves the live forward test could not be curve-fit after the fact.
We demonstrate it on our own strategy, which the system correctly shows has **no statistically
significant edge** over the tested window. **The point is the trustworthy measurement, not the
strategy. A weak result, honestly measured, is the demonstration working.**

> The LLM only authors the strategy *spec*; it never touches execution, data, or results.
> Everything downstream of the spec file is pure, deterministic Python. That separation is the
> entire design — the verification system is the contribution; the strategy is just the test subject.

| | |
|---|---|
| **Contract (BSC mainnet)** | [`0xB87481e29b0Dce9545b1B00b8526810679B521c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1) — source-verified on BscScan |
| **One-command proof (offline)** | `make verify` — full PASS/FAIL scoreboard, no secrets, no network |
| **Live checks (needs CMC key + data)** | `make verify-full` |

---

## The problem it solves

AI makes plausible-looking trading strategies cheap to generate. The trouble is that a backtest
*cannot* be trusted on its face: an overfit equity curve and a genuinely-skilled one look
identical on paper, and anyone can quietly re-tune parameters until the forward numbers look
good. Regime Pilot is the **trust layer** for that problem. It measures a strategy three ways
that are each hard to fake:

1. **Deterministic, lookahead-free backtest** — byte-identical reruns; a guard rejects any read
   of data at or after the decision time.
2. **A falsification battery** — walk-forward selection, parameter perturbation, a time-shuffle
   canary, the deflated Sharpe ratio, and feature ablation — all aimed at *disproving* the edge.
3. **On-chain commit-reveal** — every hour the live strategy's signal hash is notarized on BNB
   Smart Chain *before the hour plays out*, so the forward test provably cannot be curve-fit
   after the fact.

## How it works

```
 plain-English intent
        │   skill/   (the CMC Strategy Skill — the ONLY LLM in the system)
        ▼
   strategy spec (JSON, schema-validated, closed predicate AST)            spec/
        │
        ▼
 deterministic backtest engine  ───────────────►  falsification battery        falsify/
   engine/  (no-lookahead, byte-identical)         (walk-forward, perturbation,
        │                                            shuffle canary, deflated
        │                                            Sharpe, ablation)
        ▼
 frozen spec ─► hourly committer ─► SignalAttestor.sol on BSC (commit-reveal)  attest/
        │            (cron, hourly)                       │
        └──────────► reveal + independent verification ◄──┘
                                                          │
                          x402 data-cost plan  ◄──────────┘                     x402plan/
                          (one real $0.01 USDC paid on Base)
```

**The LLM is quarantined upstream of the spec file.** It turns a natural-language idea into a
schema-validated JSON spec with a closed predicate grammar. Nothing it emits can reach
execution: the engine reads only the validated spec, and the same spec backtested twice produces
byte-identical output (`make verify-engine`). That is what makes the measurement reproducible by
anyone.

## The differentiator: a forward test that can't be faked

Every hour a cron computes the frozen strategy's signal from public data and commits a **hash**
of it on-chain. The signal is computed only from data **strictly before** the decision hour T
(≤ T−1h), and the commit lands **within the first minutes of hour T, before essentially all of
the T→T+1h outcome is realized** — so it is a genuine forward prediction, not a hindsight pick.

```
signal      = {spec_version, spec_hash, universe_hash, timestamp_utc, regime, target_weights}
commit_hash = keccak256( canonical_json(signal) || salt )
salt        = keccak256( ATTEST_SALT_SEED || timestamp_utc )   # deterministic → reproducible at reveal
```

**Audit one commit in ~60 seconds:** read `getCommit(id)` on BscScan for the on-chain hash and
block timestamp; recompute `keccak256(canonical_json(revealed_signal) || salt)`; confirm it
matches and that the block timestamp predates the outcome window. `make attest-verify` does this
for **every** on-chain commit — it iterates the contract's own `commitCount()` so no commit can
be silently omitted — and writes `attest/VERIFICATION.md`. The contract source is verified on
BscScan (exact bytecode + ABI). See `attest/RECONCILIATION.md` for the full accounting of every
on-chain id (including two documented duplicate commits, ids 7 and 26).

## Results, honestly

The backtest window was a severe bear market: **BTC −44.7%**. Read these in order.

**1. Full-window result (the headline).**

| Version | Full-window return | vs BTC −44.7% | Annualized Sharpe | Max drawdown |
|---|--:|--:|--:|--:|
| **v1 (long-only)** | **−10.4%** | +34.3 pp | −2.20 | 12.4% |
| **v2 (long/short, live)** | **−10.9%** | +33.9 pp | −1.69 | 14.0% |

v1's −10.4% in a −44.7% market is **capital preservation, not alpha** — it routed to cash
through the decline. v2's full-window return is *slightly worse* than v1's; we do not present v2
as an improvement on the headline number.

**2. Walk-forward selection — all negative.** Every configuration in the walk-forward selection
grid was negative for both versions (v1 grid Sharpes ≈ −2.2 to −2.9; v2 ≈ −1.9 to −3.2). There
is no configuration of this strategy that was positive in-sample over this window.

**3. The one favourable slice — a single out-of-sample window, not representative.** On the held-out
embargo window the selected config returned **+1.8%** at Sharpe ~3.0. This is a **single
out-of-sample window** of ~30 days; with the full-window and walk-forward evidence above, it is
**not representative** and we do not headline it.

**4. Deflated Sharpe ≈ 0.01.** Accounting for the 27 configurations tried (Bailey & López de
Prado), the deflated Sharpe is **0.012 (v1)** and **0.013 (v2)** — i.e. **no statistically
significant directional edge** over this window, for either version. The shuffle canary passes
(edge vanishes on time-shuffled data ⇒ no lookahead/leakage) and results are robust to ±20%
parameter perturbation. The live, on-chain forward test is the real arbiter.

## Design decisions

- **Deterministic engine.** Decisions at hour T use features built from data ≤ T−1h (every
  feature series is shifted one hour); weights fill at the close of T (~1h signal-to-fill
  latency). No-lookahead is enforced by the shift *and* a `GuardedAccessor` that raises on any
  raw read at index ≥ T. *Why:* simple, conservative, provably leak-free, byte-identical.
- **Percentile / economic-logic thresholds, not a parameter search.** Regime thresholds are set
  by economic logic and symmetry rather than fitted, keeping the number of trials low (27) so the
  deflated-Sharpe penalty stays honest.
- **Commit-reveal attestation.** A deterministic salt (`keccak(seed || timestamp)`) lets an
  ephemeral runner commit without persisting secrets, yet reproduce the exact salt at reveal.
  *Why:* the forward record cannot be back-dated or re-tuned.
- **Hybrid data (documented).** Historical OHLCV for the backtest comes from a free public source;
  the CMC Fear & Greed sentiment feature and the live/forward signal inputs are CMC-native. *Why:*
  a real 12-month backtest at $0 within the operator's free CMC tier, which blocks historical
  price endpoints. See *Honest limitations* and `DATA_SOURCES.md`.
- **Interim 15-token universe.** The engine is universe-agnostic; switching to the official
  149-token list is a one-line config change (`make verify-universe`). *Why:* the team's official
  list / first-party symbol resolution was not available during the build.

(Full rationale in `DECISIONS.md`.)

## Honest limitations

- **Hybrid data.** Backtest prices are sourced from a free public OHLCV source; CMC supplies the
  sentiment feature, the live forward signal inputs, and the x402 derivatives proof. CMC Pro was
  not available during the build; wiring it is an optional config upgrade that improves data
  *coherence* (first-party CMC prices, longer history, derivatives) but is **not** expected to
  manufacture an edge — see `DATA_PLAN.md` and `DATA_SOURCES.md`.
- **Interim universe.** 15 liquid majors pending the brief's official 149-token list
  (`spec/universe_official_149.json` ships ready; flip with one config line).
- **Ranking proxy.** Assets are ranked by 24h dollar-volume (circulating-supply / market-cap
  history is not on the free tier).
- **Owner-only verification until reveal.** Payloads + salts are sealed until the reveal on
  June 20–21; until then judges verify the *hashes and timing* on-chain, not the cleartext signals.
- **Zero trades executed.** This is a measurement system; it places no orders. All timestamps UTC.
- **Backtested and attested-forward performance does not predict future results.**

(Full assumption ledger, each tagged VERIFIED/UNVERIFIED, in `ASSUMPTIONS.md`.)

## Reproduce it yourself

```bash
make setup            # install pinned deps (Python 3.12)
make verify           # OFFLINE scoreboard — no secrets, no network, no downloaded data
```
`make verify` runs on a fresh clone using a committed synthetic fixture and a committed snapshot
of the on-chain ledger. For the live checks:
```bash
make verify-full      # live: needs a CMC API key + `make data` (downloads market data)
```

| Claim | Command |
|------|---------|
| Bad specs are rejected; good ones accepted | `make verify-spec` |
| Backtest is **deterministic** (byte-identical reruns) | `make verify-engine` |
| **No lookahead** (guard rejects future reads; features use data ≤ T−1) | `make verify-engine` |
| Drawdown-budget sizing + de-risk ladder are correct | `make verify-engine` |
| Cached price data has no gaps or duplicates and matches its source within tolerance | `make verify-data` |
| The Skill is installable + the LLM is quarantined | `make verify-skill` |
| Falsification is complete and the shuffle canary passes | `make verify-falsification` |
| Every on-chain commit is accounted for and reproduces | `make attest-verify` |
| The duplicate-commit race is closed | `make verify-attest-race` |
| The x402 payment was real and the plan recomputes | `make verify-x402` |
| The repo leaks no secrets (files **and** git history) | `make verify-secrets` |

## x402 data-cost plan (real payment)

We executed **one real $0.01 USDC x402 payment on Base** (gasless EIP-3009, settled — wallet
1.5000 → 1.4900 USDC, HTTP 200, data delivered; `evidence/x402_executed_payment.json`).
`x402plan/DATA_PLAN.md` recomputes per-feed weekly cost, the minimal viable feed set, the
net-of-cost out-of-sample return, and the break-even capital (~$400) below which free data wins.
x402 also unlocks first-party CMC derivatives (funding / open interest) that the free REST tier
blocks — material for a future strategy version.

## Reveal runbook & status

The forward record accrues hourly now; the **reveal runs June 20–21**. On reveal day:

```bash
make attest-reveal        # writes reveals.json + revealed_payloads.json (publishes payloads+salts)
make attest-verify        # recomputes every on-chain hash from the revealed payloads → VERIFICATION.md
```
Expected: every revealed payload recomputes to its on-chain hash, and every block timestamp
predates its outcome window — the report ends "N on-chain commits, all accounted for." This is a
**replay** of a procedure already rehearsed end-to-end against a real EVM
(`attest/REVEAL_DRYRUN.md`), so reveal day holds no surprises. Live status any time:
`make attest-status`. See `STATUS.md` for the current scoreboard.

## Repo layout

| Path | Contents |
|------|----------|
| `skill/` | the installable CMC Strategy Skill: `SKILL.md`, `compiler_prompt.md`, example intents |
| `spec/` | `schema.json` + `regime_pilot.spec.json` (v1) + `regime_pilot_v2.spec.json` (v2) + `universe.json` + `universe_official_149.json` |
| `engine/` | deterministic backtester: `backtest.py`, `indicators.py`, `sizing.py`, `data/` fetch+cache, `datasource.py` |
| `falsify/` | falsification suite + reports + `deflated_sharpe.py` |
| `attest/` | `contracts/SignalAttestor.sol`, deploy/commit/reveal/verify, `commits_public.csv`, `onchain_ledger.json`, `RECONCILIATION.md` |
| `x402plan/` | x402 client (`pay_x402.py`), `prices.json`, `DATA_PLAN.md` |
| `cli/` | claim-based verification gates |
| `tests/` | unit tests + `fixtures/` (synthetic offline dataset) |
| `evidence/` | raw saved API responses + on-chain/payment proofs + frozen-set baseline |
| `DATA_SOURCES.md` / `DATA_PLAN.md` / `DECISIONS.md` / `ASSUMPTIONS.md` / `STATUS.md` | plain-English logs |
