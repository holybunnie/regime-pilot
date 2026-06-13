# Phase 0 — Environment Discovery Evidence

Captured: 2026-06-13 ~06:15 UTC (verified via `date -u`)
Operator-facing summary lives in `../STATUS.md`. This file is the raw record.

## Machine
| Item | Value |
|------|-------|
| OS | Ubuntu 24.04.4 LTS (Linux 6.8.0-1052-azure, x86_64) |
| Python | 3.12.1 (`/home/codespace/.python/current/bin/python3`) |
| Node | v24.14.0 |
| npm | 11.9.0 |
| git | 2.53.0 |
| curl | 8.5.0 |
| pip | 26.0.1 |
| RAM | 7.8 GiB total, ~5.8 GiB available |
| Disk | 32 GiB on /workspaces, ~20 GiB free |
| solc | NOT installed (will use solc via npm/py-solc-x or Foundry, TBD Phase 1/7) |
| forge (Foundry) | NOT installed |
| crontab | NOT present (daemon will use a long-running loop + heartbeat, not cron) |

## Network reachability (raw)
| Target | Probe | Result | Interpretation |
|--------|-------|--------|----------------|
| pro-api.coinmarketcap.com/v1/key/info | GET | HTTP 401 | REACHABLE; needs API key (none yet) |
| mcp.coinmarketcap.com/mcp | GET | HTTP 405 | REACHABLE; POST-only (streamable HTTP MCP transport) — this is the real path |
| mcp.coinmarketcap.com/sse | GET | HTTP 404 | not the SSE path; use /mcp |
| bsc-dataseed.bnbchain.org | JSON-RPC eth_chainId | `0x38` | REACHABLE; BSC mainnet (56) |
| bsc-dataseed1.binance.org | JSON-RPC eth_chainId | `0x38` | REACHABLE; BSC mainnet (56) |
| bsc.publicnode.com | JSON-RPC eth_chainId | `0x38` | REACHABLE; BSC mainnet (56) |
| data-seed-prebsc-1-s1.bnbchain.org:8545 | JSON-RPC eth_chainId | `0x61` | REACHABLE; BSC testnet (97) |
| bsc-testnet.publicnode.com | JSON-RPC eth_chainId | `0x61` | REACHABLE; BSC testnet (97) |
| github.com | GET | HTTP 200 | REACHABLE |

## Live gas (BSC mainnet)
- `eth_gasPrice` returned `0x2faf080` = 50,000,000 wei = **0.05 Gwei** (node-reported; unusually low, treat as a floor — will re-verify at deploy time in Phase 7).
- Conservative estimate using **1 Gwei**: deploy (600k) + 200 commits (50k each) + 200 reveals (40k each) ≈ 18.6M gas ≈ **0.0186 BNB** (~$11 at $600/BNB).
- At the node-reported 0.05 Gwei it would be ~$0.56. **Recommended top-up: 0.05 BNB** to be safe.

## BNB AI Agent SDK
- `bnb-chain/bnbagent-sdk`: EXISTS, Python, "Python toolkit for on-chain AI agents on BNB Chain", not archived, last push 2026-06-10, 36 stars.
- Install + capability test deferred to Phase 1 (decision rule R-Phase0.5: use it for attestation if it can deploy/interact with contracts, else fall back to web3.py/viem and document the gap in DECISIONS.md).

## CMC Skills repo (format reference)
- Official repo: **openCMC/skills-for-ai-agents-by-CoinMarketCap** (README titled "Official CoinMarketCap Skills for AI Agents"). The org name in the build prompt (`coinmarketcap-official/...`) 404s; `openCMC` is the live one. Treated as official-candidate (see ASSUMPTIONS.md).
- Skills present: cmc-mcp, market-report, crypto-research, cmc-x402, cmc-api-crypto, cmc-api-dex, cmc-api-exchange, cmc-api-market.
- Saved real SKILL.md files to evidence/ as format references: cmc-mcp, cmc-x402, crypto-research, cmc-api-crypto, market-report.
- SKILL.md format = YAML frontmatter (name, description, license, compatibility, user-invocable, allowed-tools[]) + markdown body.
- **x402 confirmed**: "$0.01 USDC per request on Base. No API key required." (from repo README) — strong basis for Phase 8.
