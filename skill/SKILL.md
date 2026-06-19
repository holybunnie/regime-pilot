---
name: regime-pilot
description: |
  Turns a natural-language trading idea into a deterministic, machine-checkable strategy spec, then backtests and falsifies it. Use whenever a user wants to design, compile, backtest, or stress-test a crypto trading strategy in plain English ("build a strategy that...", "backtest an idea where...", "what if I rotate into majors when breadth is strong").
  The LLM ONLY authors the JSON spec; a separate deterministic engine executes it and produces results, so outputs are reproducible and lookahead-proof.
  Trigger: "trading strategy", "backtest", "regime", "build a strategy", "strategy skill", "compile strategy", "/regime-pilot"
license: MIT
allowed-tools:
  - Read
  - Write
  - Bash
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_crypto_metrics
---

# Regime Pilot — Strategy Compiler Skill

You compile a user's natural-language trading intent into a **strategy spec** — a strict JSON
document validated against `spec/schema.json` — and hand it to a deterministic backtest engine.

## Core Principle

**You author the spec; you never compute results.** The spec is a closed, auditable description
(a small predicate AST — no free-form code). Everything downstream (features, regimes, sizing,
fills, PnL, falsification, on-chain attestation) is pure, deterministic Python in `engine/` and
`falsify/`. This separation is the whole point: an LLM's nondeterminism is quarantined upstream of
the spec file, so the same spec always produces byte-identical results. Never edit engine code to
make a strategy "work"; only change the spec.

## Prerequisites

- The repo's schema at `spec/schema.json` (the contract you must satisfy).
- The validator `cli/validate_spec.py` and engine `engine/backtest.py`.
- Know what data the installed engine actually executes (it gates which features are legal):
  **price (per asset and BTC), 24h dollar volume, and Fear & Greed** are available.
  **Global metrics, funding rate, and open interest are NOT executable in this version.** If you
  reference an unavailable source the validator
  raises — so do not. When unsure, confirm availability with the CMC tools before designing around
  a feature.

## Compile Workflow

### Step 1 — Gather intent
Extract from the user, asking only what's missing: the market thesis (what edge?), the universe
(which assets), the entry/exit logic, how to size, and risk limits. If the user is vague, propose
sensible defaults and state them.

### Step 2 — Map intent to legal features
Translate the thesis into `features` using only available sources and these transforms:
`raw | sma | realized_vol | percentile_rank | breadth | delta`, with an optional `rank_window` to
percentile-rank any transform's output. Prefer **percentile-ranked** thresholds over absolute
constants — they are regime-robust across market conditions. If the thesis needs unavailable data,
go to "Handling impossible intents".

### Step 3 — Express logic as a closed predicate AST
Regimes and playbook entry/exit are boolean trees over features and constants ONLY:
- logical: `{"op":"and"|"or","args":[...]}`, `{"op":"not","args":[one]}`
- comparison: `{"op":">"|"<"|">="|"<="|"crosses_above"|"crosses_below","left":<operand>,"right":<operand>}`
- operand: `{"feature":"name"}` or `{"const":number}`; boolean literal: `{"const_bool":true|false}`
Give each regime a `persistence_hours` (hysteresis) so it must hold N consecutive hours before it
activates. Make the last regime a catch-all `{"const_bool":true}`.

### Step 4 — Sizing, risk, costs
- `sizing`: the drawdown-budget law `position_size = min(vol_target, k · remaining_budget / asset_vol)`.
  `asset_vol_feature` MUST point at a `realized_vol` feature. Keep `k` conservative (≤ 1).
- `risk`: `max_drawdown_budget`, `per_asset_cap`, `max_gross_exposure`, and a `derisk_ladder`
  (cut gross as the budget is consumed, e.g. 50%→0.5×, 75%→0×, 90%→0×).
- `costs`: `fee_bps`, `slippage_bps_floor`, `slippage_size_coeff`, `latency_minutes`
  (+ `short_borrow_bps_per_day` if any playbook uses `short_assets`).
- `meta.configurations_tried`: honestly count EVERY parameter configuration explored (needed for
  the deflated Sharpe). Do not undercount.

### Step 5 — Emit ONLY the JSON spec
Output the spec as a single JSON object, nothing else (no prose, no markdown fences) into a file
under `spec/` or `skill/examples/`.

### Step 6 — Validate and iterate
Run: `python cli/validate_spec.py <path>`. If it prints problems, fix the spec and rerun. Repeat
until it prints `VALID`. Do not proceed on an invalid spec.

### Step 7 — Hand off to the engine
Run `python engine/backtest.py <spec> <outdir>` for results, and `python falsify/report.py <spec>`
for the falsification report (walk-forward, perturbation, shuffle canary, deflated Sharpe,
ablation). Present results honestly (see Important Notes).

The current engine executes hourly strategies with exactly 60 minutes of signal-to-fill latency,
uses `volume_24h` for asset ranking, and supports `price`, `btc_price`, `volume_24h`, and
`fear_greed` feature sources. Do not emit optional schema fields unless the validator confirms the
installed engine supports them.

## Handling impossible intents

If the user asks for something the data cannot support (e.g. "short when funding rate flips
negative" — funding is unavailable on this tier), DO NOT fabricate a feature or silently drop the
requirement. Instead: (1) state plainly which input is unavailable and why, (2) offer the closest
legal approximation using available data (e.g. use Fear & Greed extremes + realized-vol percentile
as a fragility proxy), and (3) only compile if the user accepts the substitution. See
`skill/examples/impossible.intent.md`.

## Important Notes (honesty)

- Every reported result must state data sources and date ranges, fee/slippage assumptions, the
  number of configurations tried, and the standing disclaimer: **backtested performance does not
  predict live results; this skill triggers zero trades.**
- Prefer disproving the strategy. A high backtest return that fails the shuffle canary (edge
  survives shuffling) signals leakage — debug before trusting it. A low deflated Sharpe means the
  edge is likely a product of multiple testing — say so.
- Never claim significance the falsification report doesn't support.

## Handling Tool Failures

If CMC tools are unavailable, design from the documented available sources above and note that
live availability was not re-confirmed. If `validate_spec` or the engine errors, read the message
— it points to the exact schema/semantic violation — fix the spec, never the engine.
