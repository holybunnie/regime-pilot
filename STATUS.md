# STATUS — Regime Pilot (plain English, for the operator)

**Last updated:** 2026-06-13 06:15 UTC
**Days to freeze:** submission freezes **2026-06-21 13:00 UTC** → ~8 days left.

## Scoreboard
| Phase | State | One-line summary |
|-------|-------|------------------|
| 0 — Environment discovery | ✅ DONE | Machine, network, gas, SDK, and CMC skill format all checked with real calls; evidence saved. |
| 1 — Data layer | ⏳ BLOCKED ON YOU | Cannot start until you give me a CMC API key. |
| 2 — Spec schema | 🔜 NEXT | Can start now; does not need your input. |
| 3 — Skill (compiler) | 🔜 | Needs the schema (Phase 2). |
| 4 — Backtest engine | 🔜 | Needs schema + some cached data. |
| 5 — Flagship strategy | 🔜 | Needs engine + data. |
| 6 — Falsification report | 🔜 | Needs strategy results. |
| 7 — On-chain attestation | ⏳ PARTIAL / URGENT | Can deploy to **testnet today** with no input from you. Mainnet + live hourly commits need a funded wallet. **Every day of delay shrinks the forward-test proof.** |
| 8 — x402 data plan | 🔜 | Can capture published prices now; one real $0.01 payment needs USDC-on-Base from you (optional). |
| 9 — Packaging/demo | 🔜 | End. |
| 10 — Verify harness | 🔜 | Built incrementally per phase. |

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

## 🙋 WHAT I NEED FROM YOU (in priority order)
1. **CMC API key** — paste it into `.env` as `CMC_API_KEY`. Get it free at
   https://pro.coinmarketcap.com/account . Without it I cannot fetch any market data (Phase 1).
   As soon as you give it, I'll call `/v1/key/info` and tell you in plain English exactly which
   data your plan can access (historical OHLCV varies by plan).
2. **A funded attestation wallet** (for the on-chain proof). Steps:
   - Make a brand-new wallet (e.g. a fresh MetaMask account) used for nothing else.
   - Send it **0.05 BNB** on BNB Smart Chain.
   - Export its private key and paste into `.env` as `ATTEST_PRIVATE_KEY`.
   This is the headline differentiator and the live commits should start ASAP — but I will work on
   the testnet version today without it, so you can do this in parallel.
3. *(Optional, helps a special prize)* A Base wallet with ~$2 of USDC, key in `.env` as
   `X402_BASE_PRIVATE_KEY`, so I can execute one real $0.01 x402 payment instead of only quoting
   the published price.

## How to see Phase 0 for yourself
```
cat regime-pilot/evidence/phase0_discovery.md
```
(A `make verify-phase0` command that re-runs all these probes live will land with the Makefile in
the next step.)
