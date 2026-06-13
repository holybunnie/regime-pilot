# Regime Pilot — a CoinMarketCap Strategy Skill (BNB Hack Track 2)

> **Status: under construction (Phase 0 complete).** This README is a stub; it will become the
> judge-facing front page. See `STATUS.md` for current progress in plain English.

Regime Pilot turns a plain-English trading idea into a deterministic, machine-checkable strategy
spec, backtests it with no lookahead and no hidden randomness, tries hard to *disprove* its own
edge (walk-forward, parameter perturbation, shuffled-data canary, deflated Sharpe, feature
ablation), and **notarizes its live hourly signals on BNB Smart Chain** via commit-reveal so the
forward test provably cannot be curve-fit after the fact.

**The LLM authors the spec; it never touches execution or results.** Everything downstream of the
spec file is pure, deterministic Python.

## Architecture (planned)
```
plain-English intent
        │  (LLM Skill — the only LLM in the system)
        ▼
   strategy spec (JSON, schema-validated, closed predicate AST)
        │
        ▼
deterministic backtest engine  ──►  falsification report
        │                                  │
        ▼                                  ▼
 frozen flagship spec ──► hourly committer ──► SignalAttestor.sol on BSC (commit-reveal)
        │                                  │
        └──────────────► reveal + independent verification ◄──┘
```

## Quickstart
_Coming with the Makefile in the next phase._ The target experience:
```
make setup && make backtest && make falsify
```

## Repo layout
See the build plan; key folders: `skill/` (the CMC Skill), `spec/` (schema + flagship strategy),
`engine/` (deterministic backtester), `falsify/`, `attest/` (on-chain), `x402plan/`, `evidence/`.

## Honesty
Backtested and even attested-forward performance does **not** predict future results. This project
executes **zero trades**. All timestamps are UTC.
