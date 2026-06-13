# Phase 0b — Credential & Access Verification

Captured 2026-06-13 ~06:30 UTC. Secrets never printed; only addresses/plan facts recorded.

## CMC API key
- Valid. Plan tier: **Basic (free)** — 15,000 credits/month, 50 calls/min, 0 used.
- Endpoint access matrix (live test):

| Endpoint | error_code | Allowed? |
|----------|-----------|----------|
| /v1/cryptocurrency/map | 0 | ✅ |
| /v2/cryptocurrency/quotes/latest | 0 | ✅ |
| /v1/cryptocurrency/listings/latest | 0 | ✅ |
| /v1/global-metrics/quotes/latest | 0 | ✅ |
| /v3/fear-and-greed/latest | 0 | ✅ |
| /v3/fear-and-greed/historical | 0 | ✅ |
| /v2/cryptocurrency/ohlcv/historical | 1006 | ❌ plan-blocked |
| /v2/cryptocurrency/ohlcv/latest | 1006 | ❌ plan-blocked |
| /v2/cryptocurrency/quotes/historical | 1006 | ❌ plan-blocked |

**Consequence:** historical PRICE data is NOT available on this tier. Only live quotes + Fear &
Greed history are. This is the central data constraint for the backtest (see STATUS.md decision).

## x402 (pay-per-call) — documented surface
- Endpoints exposed via x402 (from official skill reference, saved `evidence/x402_endpoints.md`):
  `/x402/v3/cryptocurrency/quotes/latest`, `/x402/v3/cryptocurrency/listing/latest`,
  `/x402/v1/dex/search`, `/x402/v4/dex/pairs/quotes/latest`.
- **No historical OHLCV endpoint documented for x402 either.** $0.01 USDC/request on Base.
- So x402 does NOT obviously unlock historical price data (UNVERIFIED whether undocumented
  historical params work; will probe in Phase 8, but not counting on it).

## Wallet (single wallet, both chains)
- Address: `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`
- BSC mainnet BNB: **0.009 BNB** — covers ~0.0009 BNB needed at current 0.05 Gwei (~10× margin);
  but only ~0.5× the 1-Gwei worst-case (0.0186). Recommend top-up to ~0.03 BNB if gas may spike.
- Base USDC: **1.50 USDC** — ~150 x402 calls.
- Base ETH: **0.0** — acceptable; x402 uses gasless EIP-3009 `transferWithAuthorization`
  (facilitator pays gas). Verify when executing the first real payment in Phase 8.
- Key currently in `.env` as `X402_BASE_PRIVATE_KEY`. Attestation layer will read
  `ATTEST_PRIVATE_KEY` and fall back to `X402_BASE_PRIVATE_KEY` (same wallet, both our own gas).
