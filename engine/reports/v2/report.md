# Backtest Report — Regime Pilot v2 (long/short) v2.0.0

**Window:** 2025-09-16T09:00 → 2026-06-13T10:00 UTC

## Headline (net of costs)
| Metric | Strategy | BTC buy & hold |
|--------|---------:|---------------:|
| Total return | -10.86% | -44.71% |
| Max drawdown | 13.99% | 52.86% |
| Excess return vs BTC | **+33.85%** | — |
| Annualized Sharpe | -1.69 | — |
| Trades | 3757 | — |
| Avg gross exposure | 10.4% | 100% |

## Hours per regime
| Regime | Hours |
|--------|------:|
| capitulation | 821 |
| chop | 3230 |
| downtrend | 1018 |
| trend_up | 1412 |

## Disclosures (honesty rule R8)
- **Data sources:** hourly OHLCV from Binance public API (backtest prices); Fear & Greed history
  from CoinMarketCap `/v3/fear-and-greed/historical`. See DECISIONS.md for the hybrid-data rationale.
- **Costs modeled:** 10 bps fee/side + 5 bps slippage floor + size-aware slippage.
- **Configurations tried:** 27 (used by the deflated Sharpe in the falsification report).
- **Disclaimer:** Backtested performance does not predict live results. Zero trades executed.
