# Example intent — Simple BTC Momentum

## Natural-language intent
> "Keep it simple: hold the top liquid majors while Bitcoin is above its weekly average and
> sentiment isn't euphoric; otherwise go to cash. Conservative sizing."

## How the compiler maps it
- Features (minimum viable set — quotes + Fear & Greed): `btc_now` (raw), `btc_sma_7d` (sma 168h),
  `fg_level` (raw), `btc_vol` (realized_vol, for sizing).
- One active regime `risk_on`: `btc_now > btc_sma_7d AND fg_level < 80`, persistence 8h →
  hold top-5 by 24h volume. Catch-all `risk_off` → flat.
- Drawdown-budget sizing, de-risk ladder.

## Compiled spec
→ `skill/examples/momentum_simple.spec.json` (validates).

## Verify
```
python cli/validate_spec.py skill/examples/momentum_simple.spec.json   # VALID
python engine/backtest.py    skill/examples/momentum_simple.spec.json engine/reports/momentum
```

## Honest note
This is a teaching example, not a recommended strategy — on the bear-market test window it loses
money (it's long-biased). The point is to show a clean intent→spec→backtest round-trip.
