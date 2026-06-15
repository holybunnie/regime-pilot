# DATA_PLAN — current data, and the optional CMC Pro upgrade (Item 11)

## What we run on today (and why)
- **Prices / OHLCV:** free Binance public klines (`data-api.binance.vision`). The operator's CMC
  key is **free Basic tier**, which blocks all historical price endpoints (verified, error 1006),
  so a real 12-month backtest at $0 needs a free price source.
- **Sentiment:** CoinMarketCap Fear & Greed (`/v3/fear-and-greed/historical`) — genuinely
  CMC-native; feeds the live attested signal's regime.
- **Live forward signal:** computed hourly and notarized on BSC (commit-reveal).
- Full code-verified source/credential map: see `DATA_SOURCES.md`.

## CMC Pro API — prepared, not blocking
CMC Pro API access was **not available during the build**. The system ships and runs on the
documented hybrid data above. Pro is a clean, optional upgrade:

- A documented data-source abstraction (`engine/datasource.py`) selects the price/history source
  by config: default **Binance**; set `CMC_PRO_API_KEY` (or `REGIME_PILOT_PRICE_SOURCE=cmc_pro`)
  to source prices **first-party from CoinMarketCap** — with **no change to engine logic**.
  Verified by `make verify-datasource` (mocks the key; no real key required).
- The x402 path already proves first-party CMC **derivatives** (funding / open interest) are
  reachable and payable ($0.01 USDC on Base).

## What Pro changes — and what it does not
Wiring Pro improves data **coherence** (first-party CMC prices, longer history, derivatives). It is
**not expected to manufacture an edge** — the falsification result (no statistically significant
edge over the window) stands either way. If Pro arrives, CMC-sourced results will be published as a
clearly-labeled **SUPPLEMENTARY** backtest, never as a replacement of the **attested forward
record**, and never by touching the frozen committer before reveal day.

See `x402plan/DATA_PLAN.md` for the per-feed cost model, minimal viable feed set, net-of-cost
out-of-sample return, and break-even capital.
