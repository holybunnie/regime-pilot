# ASSUMPTIONS — each tagged VERIFIED or UNVERIFIED

Goal: keep the UNVERIFIED list as close to empty as possible. Observed behavior beats docs.

## VERIFIED
- **[VERIFIED]** CMC REST base `pro-api.coinmarketcap.com` is reachable (HTTP 401 without a key).
  *How:* live HTTP probe, 2026-06-13.
- **[VERIFIED]** CMC MCP lives at `https://mcp.coinmarketcap.com/mcp` and is POST-only.
  *How:* GET returned 405 (method not allowed); `/sse` and `/` returned 404.
- **[VERIFIED]** BSC mainnet RPC `bsc-dataseed.bnbchain.org` works, chainId `0x38` (56).
  *How:* JSON-RPC `eth_chainId` POST.
- **[VERIFIED]** BSC testnet RPC `bsc-testnet.publicnode.com` works, chainId `0x61` (97).
  *How:* JSON-RPC `eth_chainId` POST.
- **[VERIFIED]** The strategy skill uses valid YAML frontmatter and passes the repository's
  installability check.
- **[VERIFIED]** CMC x402 = $0.01 USDC per request on Base, no API key required.
  *How:* official repo README text.
- **[VERIFIED]** CMC Pro hourly historical OHLCV is available. A 364-day shadow cache was built for
  all 15 active assets; Fear & Greed history is also available.
- **[VERIFIED]** Binance public klines provide free hourly OHLCV with deep history.
  *How:* live call to data-api.binance.vision returned real BTCUSDT hourly rows.
- **[VERIFIED]** Attestation/x402 wallet 0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1 holds
  0.009 BNB (BSC) + 1.50 USDC (Base). *How:* live RPC eth_getBalance + ERC-20 balanceOf.

## UNVERIFIED (with risk)
- **[UNVERIFIED]** `openCMC` is the *official* CoinMarketCap GitHub org. *Risk:* low — repo README
  self-titles "Official CoinMarketCap Skills" and matches the brief, but the org has no verified
  domain set. Will cross-check against any link in the hackathon brief before final submission.
- ~~[UNVERIFIED] Which historical-data endpoints the CMC key permits.~~ **RESOLVED** — hourly
  historical OHLCV and Fear & Greed history are available under the upgraded plan.
- **[UNVERIFIED]** Real BSC gas price at deploy time. Node reported 0.05 Gwei now (suspiciously low).
  *Risk:* low — we budgeted at 1 Gwei (20× higher) and recommend a 0.05 BNB top-up. Will re-quote
  live before each batch.
- **[UNVERIFIED]** Whether the operator's CMC key also unlocks MCP tools (some MCP access is plan-gated).
  *Risk:* low — REST is the fallback data path; MCP is preferred but optional.
