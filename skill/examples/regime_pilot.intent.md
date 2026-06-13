# Example intent — Regime Pilot (flagship)

## Natural-language intent (what the user said)
> "Build a regime-aware crypto strategy on the eligible majors. When the market is broadly
> healthy — most of the universe trending up, volatility not stretched, sentiment improving — hold
> the most liquid majors. When sentiment is euphoric and volatility is rising, get out of the way.
> When everything has capitulated, scale back into BTC/BNB as fear recedes. Otherwise stay flat.
> Use percentile thresholds so it adapts, require signals to persist a few hours, and size off a
> drawdown budget with a de-risk ladder. I don't have funding-rate data."

## How the compiler maps it
- **Available data only:** prices + Fear & Greed (no funding rate — honored).
- **Signature feature:** universe **breadth** (% of eligible tokens above their 30-day mean),
  percentile-ranked → the market-internal health gauge.
- **Regimes (with hysteresis):** `capitulation` (extreme fear + extreme vol) → staged re-entry;
  `crowded_fragile` (euphoria + rising vol) → flat; `trend_up` (high breadth + moderate vol +
  improving sentiment) → hold top-liquidity majors; `chop` (catch-all) → flat.
- **Sizing:** drawdown-budget law, `k=0.5`, vol target 20%, de-risk ladder 50%/75%/90%.

## Compiled spec
→ `spec/regime_pilot.spec.json` (v1, long-only) and `spec/regime_pilot_v2.spec.json`
(v2, adds disciplined shorting of confirmed downtrends).

## Verify
```
python cli/validate_spec.py spec/regime_pilot.spec.json      # VALID
python engine/backtest.py    spec/regime_pilot.spec.json engine/reports/regime_pilot
python falsify/report.py     spec/regime_pilot.spec.json
```
