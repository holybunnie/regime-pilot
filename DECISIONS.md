# DECISIONS — significant technical choices, in plain English

## Phase 0 (2026-06-13)

1. **RPC endpoints chosen.** Mainnet `bsc-dataseed.bnbchain.org`, testnet `bsc-testnet.publicnode.com`
   — both verified answering live. We keep a backup list (binance, publicnode) for failover in the
   committer daemon.
   *Why:* avoid a single point of failure for the hourly on-chain commits.

2. **Scheduling = long-running loop, not cron.** `crontab` is absent in this Codespace.
   *Why:* the attestation committer will be a resilient long-running process with a heartbeat file
   and auto-restart, which is also more portable to "a cheap always-on box" as the brief requests.

3. **CMC skills source = `openCMC` org.** The org name in the build prompt 404s; `openCMC` is the
   live repo matching the brief. We copy its exact SKILL.md frontmatter format so our skill is
   drop-in installable. (Flagged UNVERIFIED-official in ASSUMPTIONS.md pending brief cross-check.)

4. **SDK decision deferred to Phase 1** per the build spec's decision rule: install
   `bnb-chain/bnbagent-sdk`, test whether it can deploy/call contracts; if yes use it for the
   attestation layer, if no fall back to `web3.py` and document exactly what it lacked. README will
   describe the SDK's real role honestly either way.

5. **Backtest price data = Binance free hourly OHLCV (HYBRID model).** Operator's CMC free tier
   blocks ALL historical price endpoints (verified, error 1006). Operator chose the hybrid path:
   - Historical PRICES / PnL for the backtest → Binance public klines (free, hourly, years of
     history; verified reachable and returning real data). No API key needed.
   - Sentiment regime feature → CMC `/v3/fear-and-greed/historical` (verified available on the
     free tier) — genuinely CMC-sourced.
   - Live / forward signals for the on-chain attestation → CMC live quotes (the differentiator
     stays 100% CMC-native).
   *Why:* delivers a real 12-month backtest at $0 within the operator's funding, while keeping the
   headline forward-proof CMC-native. Tradeoff (backtest prices not CMC-sourced) is documented
   openly in the reports per honesty rule R8. Alternatives (pay to upgrade CMC; forward-only) were
   presented and declined.

6. **Engine execution model.** Decisions at hour T use features built from data ≤ T-1h (every
   feature series is shifted by 1 hour); the resulting target weights fill at the close of hour T.
   At hourly granularity this models ~1h signal-to-fill latency (costs.latency_minutes ≈ 60).
   Costs = turnover × (fee_bps + slippage)/1e4, slippage = floor + coeff×(order_notional/24h_$vol).
   No-lookahead is enforced both by the shift AND a GuardedAccessor that raises on any raw read at
   index ≥ T (tested). 'flat' positions sit in cash (0 return). *Why:* simple, conservative,
   provably leak-free, and deterministic.

7. **Asset ranking uses 24h dollar-volume, not market cap.** Binance gives price+volume but not
   circulating supply, and CMC market-cap history is blocked on the free tier. So `rank_by:
   market_cap` raises a clear error; `volume_24h` (liquidity) is the supported ranking. Documented
   in ASSUMPTIONS.md; the flagship's playbooks use volume_24h / breadth.

8. **Solidity toolchain: TBD.** Neither `solc` nor Foundry is installed. Leaning toward `py-solc-x`
   (pip-installable solc) + `web3.py` to keep the whole stack Python and reproducible with one
   lockfile; will confirm in Phase 7. *Why:* one language, one lockfile, easier determinism story.
