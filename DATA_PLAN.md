# DATA_PLAN — frozen v2 data and the versioned CMC Pro cutover

## What frozen v2 runs on today
- **Prices / OHLCV:** Binance public klines (`data-api.binance.vision`). This source is retained so
  existing reports and on-chain v2 signals remain reproducible.
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
- Key presence does **not** switch sources. `REGIME_PILOT_PRICE_SOURCE` currently documents the
  intended cutover choice; the live workflow remains explicitly wired to the frozen v2 fetch path.
- CMC data is normalized separately, including correct treatment of CMC's USD quote-volume field.
- `make verify-cmc-pro` confirmed hourly access on 2026-06-19. The plan exposes 12 months of
  historical data; the shadow cache uses a 364-day window (8,735 hourly rows for each of 15 assets)
  and passes the engine's CMC-backed v2 shadow run (`make verify-data-cmc`).
- The x402 path already proves first-party CMC **derivatives** (funding / open interest) are
  reachable and payable ($0.01 USDC on Base).

## What Pro changes — and what it does not
CMC improves data **coherence**; it does not rewrite existing evidence. A CMC-only release requires:
new versioned payload/source metadata, an explicit activation hour, regenerated backtest and
falsification reports, and continued support for reproducing old v1/v2 commits from Binance data.

See `x402plan/DATA_PLAN.md` for the per-feed cost model, minimal viable feed set, net-of-cost
out-of-sample return, and break-even capital.
