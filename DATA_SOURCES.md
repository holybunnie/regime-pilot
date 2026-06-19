# DATA_SOURCES — every external source this build actually calls (code-verified)

This table is derived from the real fetch/client code, not the prose. Each row's "call site"
points at the exact file:line. `make verify-datasources` checks that every host below appears in
the code and that no code call-site host is missing from this table.

| Source (host / endpoint) | Credential | Exactly what it feeds | Free/paid | Live/cached | Call site |
|---|---|---|---|---|---|
| `data-api.binance.vision` `/api/v3/klines` | none | Historical hourly **OHLCV (close + volume)** for the backtest **and** the live attested signal's prices | free | cached (incremental) | `engine/data/fetch.py` (BINANCE, `_fetch_klines_page`) |
| `pro-api.coinmarketcap.com` `/v3/fear-and-greed/historical` | `CMC_API_KEY` (`X-CMC_PRO_API_KEY`) | The **Fear & Greed sentiment** series → `fg_level` / `fg_delta_7d` features → regime → **the attested signal** | authenticated | active cached input | `engine/data/fetch.py` (`fetch_fear_greed`) |
| `pro-api.coinmarketcap.com` `/v2/cryptocurrency/ohlcv/historical` | `CMC_API_KEY` (`X-CMC_PRO_API_KEY`) | Separate **CMC Pro hourly OHLCV shadow cache** for the versioned post-reveal cutover; not selected by frozen v2 | Pro | inactive shadow cache | `engine/data/cmc_pro.py` (`fetch_chunk`) |
| `pro-api.coinmarketcap.com` `/v1/key/info` | `CMC_API_KEY` | Key-validity check only (environment gate) | free | live | `cli/verify_environment.py` |
| `mcp.coinmarketcap.com` `/mcp` | none | Reachability probe only (environment gate) | free | live | `cli/verify_environment.py` |
| `mcp.coinmarketcap.com` `/x402/mcp` | `X402_BASE_PRIVATE_KEY` (Base wallet, EIP-3009) | The one **real $0.01 USDC** paid request (CMC derivatives proof) | paid $0.01 | live, one-shot (evidence saved) | `x402plan/pay_x402.py` |
| `bsc-dataseed.bnbchain.org` / `bsc-dataseed1.binance.org` / `bsc.publicnode.com` (BSC mainnet RPC) | `ATTEST_PRIVATE_KEY` (to send tx; reads need no key) | On-chain **commit / read** of the signal hash | free RPC + gas | live | `attest/chain.py` |
| `base.publicnode.com` (Base mainnet RPC) | `X402_BASE_PRIVATE_KEY` | Base-chain settlement of the x402 payment (gasless EIP-3009) | free RPC | live, one-shot | `x402plan/pay_x402.py` |
| `bsc-testnet.publicnode.com` / `data-seed-prebsc-1-s1.bnbchain.org` / `bsc-testnet-dataseed.bnbchain.org` (BSC **testnet** RPC) | testnet key (optional) | Public-chain rehearsal only — **never** the live attested record | free | optional rehearsal | `attest/deploy.py` |

## Plain-English summary

**What the CMC API key does.** It authenticates three CoinMarketCap endpoints:
`/v3/fear-and-greed/historical`, `/v2/cryptocurrency/ohlcv/historical`, and `/v1/key/info`.
**The CMC key *does* touch the attested
signal:** the live v2 strategy's regime uses the Fear & Greed feature, and the hourly committer
refreshes that series via the CMC key on every run. The Pro OHLCV endpoint supplies only the
separate shadow cache and does **not** supply frozen v2 prices. The one real
x402 payment used the **Base wallet key** (`X402_BASE_PRIVATE_KEY`), not the CMC key. Without the
CMC key: the **offline `make verify` is unaffected** (it uses the committed synthetic fixture);
but `make verify-full` / `verify-environment` and the live Fear & Greed fetch fail.

**What the Binance source does.** `data-api.binance.vision` supplies free historical hourly OHLCV
(prices + volume) for both the backtest and the live signal's prices. We use it because the
the frozen v1/v2 evidence was created with this source. CMC Pro is now available, but changing the
source in place would make historical and forward records ambiguous.

**The honest one-liner.** Frozen v1/v2 price/OHLCV = Binance public klines; sentiment = CMC.
CMC Pro is verified and the separate first-party adapter/cache are ready, but source presence does
not silently rewrite the live record. CMC-only operation requires an explicit versioned cutover.

**FROZEN-SET note.** `engine/data/fetch.py` is on the live committer's path, so both Binance
(prices) and CMC (Fear & Greed) feed the attested signals. The CMC key therefore matters to the
forward record; the Base wallet key (x402) and the `verify-environment` probes do **not**.
