# x402 Data-Cost Plan

All figures derive from a **real, live** x402 price ($0.01/request, captured from CMC's live 402
challenge) and the v2 falsification ablation — recomputed by `make verify-phase8`, not hand-typed.

## Real payment executed
A single **$0.01 USDC** request was paid and **settled on Base** (gasless, EIP-3009) — wallet went
1.5000 → 1.4900 USDC, HTTP 200, data delivered. Evidence: `evidence/x402_executed_payment.json`.

## Per-feed cost & importance (OOS impact from ablation)
| Feed | x402 price | Cadence | x402 $/week | OOS return lost if dropped | Verdict |
|------|-----------|---------|------------:|---------------------------:|:-------:|
| price | $0.01 | 168/wk | $1.68 | +1.81% | **KEEP** |
| fear_greed | n/a (not on x402) | 7/wk | — | +2.59% | **KEEP** |

- **Minimal viable feed set:** price, fear_greed.
- Fear & Greed is **not** sold via x402; it stays free on the CMC v3 REST endpoint.
- x402 additionally **unlocks** get_global_crypto_derivatives_metrics (funding/OI) — blocked on free REST tier — useful for a future strategy version.

## Cost to run live
- **Today: $0.00/week.** The strategy runs entirely on free sources
  (Binance klines + CMC free tier), so there is no live data bill.
- **If priced via x402 instead:** $1.68/week
  (≈ $7.20/month), dominated by the hourly price feed.

## Performance net of data cost
- Flagship v2 out-of-sample (embargo, ~30d) gross return: **+1.79%**.
- Net of **free** sources used today: **+1.79%** (cost $0).
- The x402 cost is **fixed** ($/month), so it only erodes a percentage return below a capital
  threshold. **Break-even capital ≈ $402** — above that, the
  monthly x402 bill is smaller than the OOS return; below it, use the free sources (which we do).

*Backtested/out-of-sample performance does not predict live results. This project executes zero trades.*
