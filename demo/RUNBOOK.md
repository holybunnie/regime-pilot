# Demo Runbook

All assets here regenerate offline via `make demo` (< 5 min) from frozen published reports, the
committed ledger snapshot, and the local BTC cache.

## Three-minute walkthrough

### 0:00–0:25 — Problem and claim

Show the README title.

“AI can produce unlimited plausible backtests. The hard problem is proving which results deserve
trust. Regime Pilot turns natural-language intent into a closed strategy spec, then measures it
with deterministic execution, adversarial falsification, and an on-chain forward record.”

### 0:25–0:55 — Intent becomes measurable

Show `skill/examples/regime_pilot.intent.md`, then `spec/regime_pilot_v2.spec.json`.

“The LLM stops here. It authors a schema-validated JSON spec; it never touches prices, execution,
or results. From this file onward, the same inputs produce the same outputs. `make verify` checks
that boundary offline on a clean machine.”

### 0:55–1:40 — The honest result

Show `equity_v1_v2_vs_btc.png`, then `falsify__REPORT_regime_pilot_v2.spec.md`.

“Here is the result most strategy demos would hide. The historical backtest covers September 16,
2025 through June 13, 2026; 2025 is the start of the tested data, not the report date. In that
frozen window, v1 returned minus 10.4 percent and v2 minus 10.9 percent while BTC fell 44.7
percent. That is defensive capital preservation, not statistically significant alpha.
Walk-forward folds were negative, and after penalizing 27 trials the deflated Sharpe is 0.013.
The favorable 1.8 percent slice is shown only after the full-window result because it is one small
out-of-sample window.”

“Our own verifier told us our own strategy has no demonstrated directional edge. That is the
product working. A verifier that only says yes when its creators want yes is worthless.”

### 1:40–2:30 — Proof that cannot be backdated

Show the BscScan contract, one old transaction, then `attest__VERIFICATION.md`.

“Each decision-hour signal is reduced to a hash and committed to BNB Smart Chain before that
hour’s outcome. The block timestamp is the chain’s clock, not ours. The current public ledger has
148 primary predictions; two duplicate transactions are disclosed as ids 7 and 26,
and 4 decision hours are missing, for 97.4% coverage through June 19 at 14:00 UTC.
Nothing is silently dropped: the verifier starts from the contract’s own commit count.”

“Before reveal, this proves existence, ordering, timing, and complete accounting while payloads
remain sealed. After reveal, `make attest-verify` also recomputes each payload and salt against its
on-chain hash.”

### 2:30–3:00 — Reproducibility and close

Show the `make verify` result, then `x402plan__DATA_PLAN.md`.

“Thirteen offline gates and seventeen tests pass. The data plan also records a real one-cent USDC
x402 payment and reports economics net of measured data cost.”

“Regime Pilot is not a promise of future profit. It is a filter for AI-generated strategies:
closed specification, deterministic measurement, active attempts to disprove the edge, and a
forward record that cannot be rewritten after the outcome. Three commands reproduce the evidence:
`make verify`, `make demo`, and `make attest-verify`.”

*Backtested/forward performance does not predict future results. Zero trades executed.*
