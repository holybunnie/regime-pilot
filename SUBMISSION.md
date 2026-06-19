# Regime Pilot — Submission

## One-line pitch

Regime Pilot is a CoinMarketCap strategy-compiler Skill plus a deterministic verification system
that tries to disprove an AI-authored strategy’s edge and seals its forward signals on-chain before
their outcomes.

## What we built

The Skill converts plain-English trading intent into a schema-validated JSON strategy spec. The LLM
stops at that boundary. Deterministic Python then:

1. runs a lookahead-guarded, cost-aware backtest;
2. applies walk-forward testing, parameter perturbation, a shuffle canary, feature ablation, and
   the deflated Sharpe ratio; and
3. commits each forward signal’s hash to a source-verified BSC mainnet contract before the outcome
   window.

The contribution is the verification system, not a claim that the example strategy is profitable.

## Prize tracks targeted

### Primary: Track 2 — Strategy Skills

Regime Pilot is built specifically for Track 2. Its deliverables are an installable CMC Skill and
a backtestable, schema-validated strategy spec. No execution layer is required for this track.

Track 2 fit:

- natural-language strategy intent is compiled into a closed JSON specification;
- CMC Fear & Greed is an active strategy input;
- the generated strategy is reproducible, cost-aware, and protected against lookahead;
- the falsification system tests whether the measured edge survives walk-forward validation,
  perturbation, shuffling, feature ablation, and multiple-testing correction; and
- the BSC commit-reveal record adds tamper-evident forward evidence beyond a conventional
  backtest.

### Special prize: Best Use of Agent Hub

Regime Pilot targets the cross-track **Best Use of Agent Hub** prize. The Agent Hub is substantive
to the project rather than a cosmetic API call:

- the installable CMC Skill is the strategy-authoring interface;
- authenticated CMC Fear & Greed directly changes the strategy regime and target weights;
- CMC Pro hourly OHLCV support is implemented and verified in a separate versioned shadow path;
- one real CMC x402 request was paid with **$0.01 USDC on Base**, returned data successfully, and
  feeds a reproducible data-cost and break-even-capital plan; and
- the repository verifies the Skill boundary, CMC data capabilities, source provenance, x402
  settlement evidence, and deterministic downstream execution.

Regime Pilot does **not** claim the Trust Wallet Agent Kit or BNB AI Agent SDK special prizes,
because neither is used as a core execution dependency.

## Honest result

The frozen historical backtest covers **September 16, 2025 through June 13, 2026**. The 2025 date
is the start of the tested data, not the report date. It was a severe bear-market window in which
BTC returned **−44.7%**.

- v1 returned **−10.4%** with 12.4% maximum drawdown.
- the attested v2 version returned **−10.9%** with 14.0% maximum drawdown.
- walk-forward selection folds were negative.
- one favorable **+1.8%** out-of-sample slice is disclosed only after the full-window result and is
  not treated as representative.
- deflated Sharpe was **0.012 for v1** and **0.013 for v2** after 27 trials.

Verdict: **no statistically significant directional edge over the tested window**. This negative
verdict is intentional evidence that the verifier does not flatter its creators.

## Tamper-evident forward record

- Contract: [`0xB87481e29b0Dce9545b1B00b8526810679B521c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1)
- Network: BNB Smart Chain mainnet
- Public record through **2026-06-19T14:00Z**: **148 primary predictions across 152 decision
  hours (97.4% coverage)**
- Disclosures: four missing decision hours and two byte-identical duplicate transactions, ids 7
  and 26
- Reconciliation: [`attest/RECONCILIATION.md`](attest/RECONCILIATION.md)

Before reveal, the chain proves hash existence, ordering, timestamp, and complete accounting while
the payloads remain sealed. After reveal, `make attest-verify` recomputes each published payload and
salt and compares it with the on-chain hash.

## CoinMarketCap and x402

CMC Fear & Greed is an active strategy input. CMC Pro hourly OHLCV is implemented and verified in a
separate shadow cache; it is not silently substituted into the frozen Binance-priced v1/v2 record.
The project also completed one real **$0.01 USDC x402 payment on Base**, with a deterministic
net-of-data-cost plan.

## Reproduce

One-time setup on macOS or Linux:

```bash
git clone https://github.com/holybunnie/regime-pilot.git
cd regime-pilot
python3 -m venv .venv
source .venv/bin/activate
make setup
make verify          # 13 offline claim gates; no key or network required
python3 -m pytest -q # 17 tests
make demo            # regenerates the presentation bundle from local cache
make attest-verify   # chain-complete accounting; recomputes payloads after reveal
```

Installing the pinned dependencies with `make setup` requires internet access once. The core
`make verify` command is then offline. In later terminal sessions, activate the environment again
with `source .venv/bin/activate`.

Final check on June 19, 2026: all 13 offline gates, all 17 tests, the full live verification suite,
CMC Pro capability, both data caches, the strategy run, and the BSC contract check passed.

## Three-minute demo

Use [`demo/RUNBOOK.md`](demo/RUNBOOK.md). The presentation order is:

1. problem and claim;
2. intent-to-spec boundary;
3. negative result and falsification;
4. on-chain timestamp and complete accounting;
5. reproducibility, measured data cost, and limitations.

## Links

- Repository: <https://github.com/holybunnie/regime-pilot>
- Contract: <https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1>
- Verified commands and architecture: [`README.md`](README.md)
- Current operator status: [`STATUS.md`](STATUS.md)
- Data provenance: [`DATA_SOURCES.md`](DATA_SOURCES.md)

## Standing disclosure

Backtested and sealed-forward performance does not guarantee future results. Regime Pilot measures
demonstrated edge over tested data; it does not predict the future. Zero trades were executed.
