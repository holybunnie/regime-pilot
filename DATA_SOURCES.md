# DATA_SOURCES — every external source this build actually calls (code-verified)

This table is derived from the real fetch/client code, not the prose. Each row's "call site"
points at the exact file:line. `make verify-datasources` checks that every host below appears in
the code and that no code call-site host is missing from this table.

| Source (host / endpoint) | Credential | Exactly what it feeds | Free/paid | Live/cached | Call site |
|---|---|---|---|---|---|
| `data-api.binance.vision` `/api/v3/klines` | none | Historical hourly **OHLCV (close + volume)** for the backtest **and** the live attested signal's prices | free | cached (incremental) | `engine/data/fetch.py` (BINANCE, `_fetch_klines_page`) |
| `pro-api.coinmarketcap.com` `/v3/fear-and-greed/historical` | `CMC_API_KEY` (`X-CMC_PRO_API_KEY`) | The **Fear & Greed sentiment** series → `fg_level` / `fg_delta_7d` features → regime → **the attested signal** | free tier | cached | `engine/data/fetch.py` (`fetch_fear_greed`) |
| `pro-api.coinmarketcap.com` `/v1/key/info` | `CMC_API_KEY` | Key-validity check only (environment gate) | free | live | `cli/verify_environment.py` |
| `mcp.coinmarketcap.com` `/mcp` | none | Reachability probe only (environment gate) | free | live | `cli/verify_environment.py` |
| `mcp.coinmarketcap.com` `/x402/mcp` | `X402_BASE_PRIVATE_KEY` (Base wallet, EIP-3009) | The one **real $0.01 USDC** paid request (CMC derivatives proof) | paid $0.01 | live, one-shot (evidence saved) | `x402plan/pay_x402.py` |
| `bsc-dataseed.bnbchain.org` / `bsc-dataseed1.binance.org` / `bsc.publicnode.com` (BSC mainnet RPC) | `ATTEST_PRIVATE_KEY` (to send tx; reads need no key) | On-chain **commit / read** of the signal hash | free RPC + gas | live | `attest/chain.py` |
| `base.publicnode.com` (Base mainnet RPC) | `X402_BASE_PRIVATE_KEY` | Base-chain settlement of the x402 payment (gasless EIP-3009) | free RPC | live, one-shot | `x402plan/pay_x402.py` |
| `bsc-testnet.publicnode.com` / `data-seed-prebsc-1-s1.bnbchain.org` / `bsc-testnet-dataseed.bnbchain.org` (BSC **testnet** RPC) | testnet key (dry-run only) | Item-3 reveal rehearsal on testnet — **never** the live attested record | free | live (rehearsal only) | `attest/deploy.py` |

## Plain-English summary

**What the CMC API key does.** It authenticates two CoinMarketCap endpoints:
`/v3/fear-and-greed/historical` (the Fear & Greed sentiment series) and `/v1/key/info` (a
validity check used only by the environment gate). **The CMC key *does* touch the attested
signal:** the live v2 strategy's regime uses the Fear & Greed feature, and the hourly committer
refreshes that series via the CMC key on every run. It does **not** supply prices. The one real
x402 payment used the **Base wallet key** (`X402_BASE_PRIVATE_KEY`), not the CMC key. Without the
CMC key: the **offline `make verify` is unaffected** (it uses the committed synthetic fixture);
but `make verify-full` / `verify-environment` and the live Fear & Greed fetch fail.

**What the Binance source does.** `data-api.binance.vision` supplies free historical hourly OHLCV
(prices + volume) for both the backtest and the live signal's prices. We use it because the
operator's **free CMC tier blocks all historical price endpoints** (verified, error 1006), so a
real 12-month backtest at $0 needs a free price source.

**The honest one-liner.** Price/OHLCV = Binance public klines; sentiment (Fear & Greed) + the
x402 proof = CoinMarketCap. CMC Pro would let prices *also* come first-party — a data-coherence
upgrade, wired but optional (see Item 11 / `DATA_PLAN.md`); it is not expected to manufacture an
edge, and the attested forward record stands either way.

**FROZEN-SET note.** `engine/data/fetch.py` is on the live committer's path, so both Binance
(prices) and CMC (Fear & Greed) feed the attested signals. The CMC key therefore matters to the
forward record; the Base wallet key (x402) and the `verify-environment` probes do **not**.
