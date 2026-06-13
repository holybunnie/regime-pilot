# Falsification Report — Regime Pilot v2 (long/short) v2.0.0

Embargoed out-of-sample window begins **2026-05-14** and is evaluated once, last.

## Executive summary (plain English)

This report tries to *disprove* the strategy's edge five ways. **Shuffle canary:** pass — edge vanished on shuffled data (as it should) — when we destroy the time-order of returns the edge disappears, as a real (non-leaking) strategy should. **Parameter sensitivity:** robust (degrades smoothly) (worst return swing +2.6% when every threshold is moved ±20%). **Deflated Sharpe** (after accounting for 27 configurations tried) is **0.01** — it does NOT clear the multiple-testing bar (likely no real edge). **Walk-forward** picks parameters only on past data; the embargoed window returns +1.3%. **Ablation** shows which inputs matter (below). Backtested and forward performance do not predict future results; this project executes zero trades.

## 1. Walk-forward (out-of-sample by construction)

| Fold | Train ≤ | Validate < | Selected config | Val Sharpe | Val return |
|--:|----|----|----|--:|--:|
| 1 | 2025-11-03 | 2025-12-21 | p12_k0.3_b55 | -5.32 | -6.9% |
| 2 | 2025-12-21 | 2026-02-07 | p12_k0.3_b55 | -0.84 | -1.4% |
| 3 | 2026-02-07 | 2026-03-27 | p12_k0.5_b55 | -3.02 | -2.6% |
| 4 | 2026-03-27 | 2026-05-14 | p12_k0.3_b55 | -0.38 | -0.3% |

**Embargoed window (evaluated once, last)** — config `p12_k0.3_b55` chosen on pre-embargo data: return +1.3%, Sharpe 1.95, maxDD 1.5% over 721 hours.

## 2. Parameter perturbation (±20% each)

Baseline pre-embargo return -12.5%, Sharpe -2.18. **Verdict: ROBUST (degrades smoothly)** (max abs return swing +2.6%).

| Param change | Return | Sharpe | Max DD | Δ return |
|----|--:|--:|--:|--:|
| k -20% | -12.8% | -2.31 | 14.1% | -0.4% |
| vol_target -20% | -12.3% | -2.22 | 13.9% | +0.2% |
| max_dd_budget -20% | -11.7% | -2.43 | 12.0% | +0.8% |
| fg_extremes -20% | -12.2% | -2.08 | 13.7% | +0.3% |
| vol_pct_thr -20% | -12.3% | -2.44 | 13.9% | +0.2% |
| breadth_thr -20% | -9.8% | -1.62 | 12.9% | +2.6% |
| k +20% | -12.3% | -2.14 | 13.9% | +0.2% |
| vol_target +20% | -13.1% | -2.31 | 14.5% | -0.7% |
| max_dd_budget +20% | -13.8% | -2.29 | 15.4% | -1.4% |
| fg_extremes +20% | -12.2% | -2.06 | 13.7% | +0.3% |
| vol_pct_thr +20% | -13.4% | -1.66 | 14.8% | -0.9% |
| breadth_thr +20% | -12.4% | -1.96 | 13.3% | +0.0% |

## 3. Shuffled-data canary

Fixed seed 20260613. Real: return -12.5%, Sharpe -2.18. Shuffled: return -6.1%, Sharpe -1.65.

**PASS — edge vanished on shuffled data (as it should)**


## 4. Deflated Sharpe ratio

- Observed annualized Sharpe: **-1.69** (6481 hourly obs, skew 0.22, kurtosis 41.01)
- Configurations tried (trials): **27**; variance of trial Sharpes: 2.27e-05
- Deflated benchmark SR* (per period): 0.00967
- **Deflated Sharpe Ratio: 0.013** — does NOT clear the multiple-testing bar (likely no real edge)
- Reference: Bailey & Lopez de Prado (2014), The Deflated Sharpe Ratio

## 5. Feature ablation (out-of-sample)

Full model OOS: return +1.8%, Sharpe 2.98.

| Dropped feature | OOS return | OOS Sharpe | Return degradation |
|----|--:|--:|--:|
| breadth_30d | +1.8% | 2.98 | +0.0% |
| breadth_pct | +2.9% | 4.65 | -1.1% |
| fg_level | +1.6% | 2.62 | +0.2% |
| fg_delta_7d | -0.8% | -3.34 | +2.6% |
| btc_vol | +1.8% | 2.98 | +0.0% |
| btc_vol_pct | +0.1% | 0.99 | +1.7% |
| btc_now | -0.0% | -0.21 | +1.8% |
| btc_sma_30d | -0.0% | -0.21 | +1.8% |

---
*Disclaimer: backtested performance does not predict live results. This project executes zero trades. Data: Binance hourly OHLCV + CoinMarketCap Fear & Greed.*
