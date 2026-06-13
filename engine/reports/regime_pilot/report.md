# Backtest Report — Regime Pilot v1.0.0

**Window:** 2025-09-16T06:00 → 2026-06-13T07:00 UTC

## Headline (net of costs)
| Metric | Strategy | BTC buy & hold |
|--------|---------:|---------------:|
| Total return | -10.38% | -44.96% |
| Max drawdown | 12.43% | 52.86% |
| Excess return vs BTC | **+34.57%** | — |
| Annualized Sharpe | -2.20 | — |
| Trades | 2402 | — |
| Avg gross exposure | 7.6% | 100% |

## Hours per regime
| Regime | Hours |
|--------|------:|
| capitulation | 924 |
| chop | 4043 |
| trend_up | 1514 |

## Disclosures (honesty rule R8)
- **Data sources:** hourly OHLCV from Binance public API (backtest prices); Fear & Greed history
  from CoinMarketCap `/v3/fear-and-greed/historical`. See DECISIONS.md for the hybrid-data rationale.
- **Costs modeled:** 10 bps fee/side + 5 bps slippage floor + size-aware slippage.
- **Configurations tried:** 27 (used by the deflated Sharpe in the falsification report).
- **Disclaimer:** Backtested performance does not predict live results. Zero trades executed.
