# Falsification Report — Regime Pilot v1.0.0

Embargoed out-of-sample window begins **2026-05-14** and is evaluated once, last.

## Executive summary (plain English)

This report tries to *disprove* the strategy's edge five ways. **Shuffle canary:** pass — edge vanished on shuffled data (as it should) — when we destroy the time-order of returns the edge disappears, as a real (non-leaking) strategy should. **Parameter sensitivity:** robust (degrades smoothly) (worst return swing +2.9% when every threshold is moved ±20%). **Deflated Sharpe** (after accounting for 27 configurations tried) is **0.01** — it does NOT clear the multiple-testing bar (likely no real edge). **Walk-forward** picks parameters only on past data; the embargoed window returns +0.2%. **Ablation** shows which inputs matter (below). Backtested and forward performance do not predict future results; this project executes zero trades.

## 1. Walk-forward (out-of-sample by construction)

| Fold | Train ≤ | Validate < | Selected config | Val Sharpe | Val return |
|--:|----|----|----|--:|--:|
| 1 | 2025-11-03 | 2025-12-21 | p4_k0.3_b55 | -6.68 | -5.4% |
| 2 | 2025-12-21 | 2026-02-07 | p4_k0.3_b55 | -2.15 | -3.1% |
| 3 | 2026-02-07 | 2026-03-27 | p12_k0.3_b55 | -2.28 | -1.7% |
| 4 | 2026-03-27 | 2026-05-14 | p8_k0.5_b55 | 0.52 | +0.4% |

**Embargoed window (evaluated once, last)** — config `p8_k0.5_b55` chosen on pre-embargo data: return +0.2%, Sharpe 0.85, maxDD 0.8% over 720 hours.

## 2. Parameter perturbation (±20% each)

Baseline pre-embargo return -10.7%, Sharpe -2.43. **Verdict: ROBUST (degrades smoothly)** (max abs return swing +2.9%).

| Param change | Return | Sharpe | Max DD | Δ return |
|----|--:|--:|--:|--:|
| k -20% | -10.8% | -2.49 | 12.5% | -0.1% |
| vol_target -20% | -10.2% | -2.36 | 11.9% | +0.5% |
| max_dd_budget -20% | -9.5% | -2.21 | 11.2% | +1.2% |
| fg_extremes -20% | -10.3% | -2.28 | 12.0% | +0.4% |
| vol_pct_thr -20% | -9.0% | -2.15 | 12.7% | +1.8% |
| breadth_thr -20% | -7.8% | -1.49 | 11.8% | +2.9% |
| k +20% | -10.7% | -2.43 | 12.4% | +0.0% |
| vol_target +20% | -10.9% | -2.46 | 12.6% | -0.2% |
| max_dd_budget +20% | -12.3% | -2.66 | 14.0% | -1.6% |
| fg_extremes +20% | -10.2% | -2.15 | 11.8% | +0.5% |
| vol_pct_thr +20% | -11.7% | -2.63 | 13.4% | -1.0% |
| breadth_thr +20% | -10.6% | -2.31 | 11.5% | +0.1% |

## 3. Shuffled-data canary

Fixed seed 20260613. Real: return -10.7%, Sharpe -2.43. Shuffled: return -8.0%, Sharpe -2.91.

**PASS — edge vanished on shuffled data (as it should)**


## 4. Deflated Sharpe ratio

- Observed annualized Sharpe: **-2.20** (6481 hourly obs, skew -2.16, kurtosis 51.52)
- Configurations tried (trials): **27**; variance of trial Sharpes: 3.95e-06
- Deflated benchmark SR* (per period): 0.00403
- **Deflated Sharpe Ratio: 0.012** — does NOT clear the multiple-testing bar (likely no real edge)
- Reference: Bailey & Lopez de Prado (2014), The Deflated Sharpe Ratio

## 5. Feature ablation (out-of-sample)

Full model OOS: return +0.4%, Sharpe 2.01.

| Dropped feature | OOS return | OOS Sharpe | Return degradation |
|----|--:|--:|--:|
| breadth_30d | +0.4% | 2.01 | +0.0% |
| breadth_pct | +0.1% | 0.28 | +0.3% |
| fg_level | +0.1% | 0.62 | +0.3% |
| fg_delta_7d | -0.5% | -2.03 | +0.9% |
| btc_vol | +0.4% | 2.01 | +0.0% |
| btc_vol_pct | +0.4% | 2.06 | -0.0% |

---
*Disclaimer: backtested performance does not predict live results. This project executes zero trades. Data: Binance hourly OHLCV + CoinMarketCap Fear & Greed.*
