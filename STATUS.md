# STATUS — Regime Pilot (plain English, for the operator)

**Last updated:** 2026-06-13 07:00 UTC
**Days to freeze:** submission freezes **2026-06-21 13:00 UTC** → ~8 days left.

## Scoreboard
| Phase | State | One-line summary |
|-------|-------|------------------|
| 0 — Environment discovery | ✅ DONE | Machine, network, gas, SDK, CMC skill format, key tier + wallet all verified with real calls. `make verify-phase0` passes. |
| 1 — Data layer | ✅ DONE | 15 tokens × 9,361 hourly bars (390 days) + CMC Fear&Greed history cached; 0 gaps, 0 dups, cache matches live, embargo set. `make verify-phase1` passes. *(Universe is interim — see note below.)* |
| 2 — Spec schema | ✅ DONE | JSON Schema + validator + 1 example + 8 malformed-rejection tests. `make verify-phase2` passes. |
| 3 — Skill (compiler) | 🔜 | Needs the schema (Phase 2). |
| 4 — Backtest engine | 🔜 | Needs schema + some cached data. |
| 5 — Flagship strategy | 🔜 | Needs engine + data. |
| 6 — Falsification report | 🔜 | Needs strategy results. |
| 7 — On-chain attestation | ⏳ PARTIAL / URGENT | Can deploy to **testnet today** with no input from you. Mainnet + live hourly commits need a funded wallet. **Every day of delay shrinks the forward-test proof.** |
| 8 — x402 data plan | 🔜 | Can capture published prices now; one real $0.01 payment needs USDC-on-Base from you (optional). |
| 9 — Packaging/demo | 🔜 | End. |
| 10 — Verify harness | 🔜 | Built incrementally per phase. |

## Key fact discovered: your CMC plan blocks price history
Your CMC key works but is the **free tier**, which does **not** allow historical price data (only
live prices + Fear & Greed history). You chose the **hybrid** plan: the backtest's historical
prices come from Binance's free public data, the sentiment signal from CMC's Fear & Greed history,
and the live on-chain proof stays 100% CMC. Cost: $0. This is documented openly in DECISIONS.md.

## Wallet (verified on-chain)
Address `0x73C0152a7dB01Cb11E257A8C82366B3EEaF53Ae1`: 0.009 BNB on BSC (attestation gas — enough at
current low gas; top up to ~0.03 BNB if you want a spike buffer) + 1.50 USDC on Base (x402, ~150
calls). No Base ETH needed (x402 is gasless for the payer).

## What I verified in Phase 0 (all with real calls, evidence in `evidence/`)
- This machine: Ubuntu 24.04, Python 3.12.1, Node 24.14, 7.8 GB RAM, 20 GB free disk. Good enough.
- CMC REST API is reachable (returns 401 = "needs your key").
- CMC MCP server is reachable at `https://mcp.coinmarketcap.com/mcp` (POST-only).
- BSC mainnet AND testnet RPC both reachable and answering. Mainnet chain id confirmed (56).
- The BNB AI Agent SDK is a real, active Python project (last updated 3 days ago).
- The official CMC skills repo is `openCMC/skills-for-ai-agents-by-CoinMarketCap`; I saved 5 real
  skill files to copy the exact installable format. Confirmed x402 = $0.01/request on Base.

## 💰 Money / wallet estimate (verified against live gas)
- Running ~200 hourly commits + reveals + one contract deploy costs roughly **0.0186 BNB** worst
  case (~$11), and as little as ~$0.56 at the gas price the network reported just now.
- **Please fund a brand-new wallet with 0.05 BNB** (≈ $30) — comfortable safety margin. Anything
  left over is yours; this project never spends BNB on anything but its own gas and executes ZERO
  trades.

## 🙋 WHAT I NEED FROM YOU
- **The official 149-token BEP-20 universe list** from the hackathon brief, when convenient.
  I've built and tested everything on a verified interim set of 15 liquid majors (BNB, BTC, ETH,
  …). The moment you paste the official list into `spec/universe.json`, `make data` re-pulls it and
  everything downstream uses it — no code changes needed. Not blocking; the engine is universe-agnostic.
- **Nothing else blocking.** CMC key, wallet (BNB + USDC) all provided and verified.
- *(Optional)* Top up the wallet to ~0.03 BNB if you want a comfortable buffer against a gas
  spike during the ~8 days of hourly commits. Not urgent at current gas prices.

## How to see the work for yourself
```
cd regime-pilot
make verify-phase0     # live-checks every dependency + your credentials
make verify-phase2     # proves the spec schema accepts valid + rejects broken specs
make verify            # runs all gates that exist so far
```
