# DATA_PLAN — frozen v2 data and the versioned CMC Pro cutover

## What we run on today (and why)
- **Prices / OHLCV:** free Binance public klines (`data-api.binance.vision`). The operator's CMC
  key is **free Basic tier**, which blocks all historical price endpoints (verified, error 1006),
  so a real 12-month backtest at $0 needs a free price source.
- **Sentiment:** CoinMarketCap Fear & Greed (`/v3/fear-and-greed/historical`) — genuinely
  CMC-native; feeds the live attested signal's regime.
- **Live forward signal:** computed hourly and notarized on BSC (commit-reveal).
- Full code-verified source/credential map: see `DATA_SOURCES.md`.

## CMC Pro API — provisioned, adapter built, not silently activated
The operator reported the API key upgraded to Pro on **2026-06-19**. The repository now includes a
real hourly historical-OHLCV adapter at `engine/data/cmc_pro.py`, stable numeric CMC IDs in
`spec/cmc_ids.json`, source-specific caching under `engine/data/cache_cmc/`, and a live capability
probe (`make verify-cmc-pro`).

- The same `CMC_API_KEY` is used; no duplicate `CMC_PRO_API_KEY` secret is required.
- Key presence does **not** switch sources. `REGIME_PILOT_PRICE_SOURCE=cmc_pro` is required.
- CMC data is normalized separately, including correct treatment of CMC's USD quote-volume field.
- `make verify-cmc-pro` confirmed hourly access on 2026-06-19. The plan exposes 12 months of
  historical data; the shadow cache uses a 364-day window (8,735 hourly rows for each of 15 assets)
  and passes the engine's CMC-backed v2 shadow run.
- The x402 path already proves first-party CMC **derivatives** (funding / open interest) are
  reachable and payable ($0.01 USDC on Base).

## What Pro changes — and what it does not
CMC improves data **coherence**; it does not rewrite the existing evidence. The Binance-backed v2
record continues through reveal. After reveal, CMC becomes a clearly versioned v3 source cutover,
with a new backtest/falsification report and source identifier. Old v1/v2 reports and commits remain
reproducible from their original source.

See `x402plan/DATA_PLAN.md` for the per-feed cost model, minimal viable feed set, net-of-cost
out-of-sample return, and break-even capital.
