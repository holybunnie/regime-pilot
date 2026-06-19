# DECISIONS — significant technical choices, in plain English

## Initial architecture (2026-06-13)

1. **RPC endpoints chosen.** Mainnet `bsc-dataseed.bnbchain.org`, testnet `bsc-testnet.publicnode.com`
   — both verified answering live. We keep a backup list (binance, publicnode) for failover in the
   committer daemon.
   *Why:* avoid a single point of failure for the hourly on-chain commits.

2. **Scheduling = GitHub Actions hourly workflow.**
   *Why:* the attestation committer needs a reproducible managed schedule with a heartbeat and
   repository-backed public record.

3. **Frozen v1/v2 price data = Binance hourly OHLCV (HYBRID model).** The original CMC tier
   blocked historical price endpoints, so the initial evidence used:
   - Historical PRICES / PnL for the backtest → Binance public klines (free, hourly, years of
     history; verified reachable and returning real data). No API key needed.
   - Sentiment regime feature → CMC `/v3/fear-and-greed/historical`.
   - Live / forward signal prices and volume → the same Binance cache, preserving consistency with
     the frozen backtest; sentiment remains CMC-native.
   CMC Pro is now verified and has its own 364-day shadow cache. It is not substituted into v1/v2
   because that would change the source beneath already-published reports and on-chain signals.

4. **Engine execution model.** Decisions at hour T use features built from data ≤ T-1h (every
   feature series is shifted by 1 hour); the resulting target weights fill at the close of hour T.
   At hourly granularity this models ~1h signal-to-fill latency (costs.latency_minutes ≈ 60).
   Costs = turnover × (fee_bps + slippage)/1e4, slippage = floor + coeff×(order_notional/24h_$vol).
   No-lookahead is enforced both by the shift AND a GuardedAccessor that raises on any raw read at
   index ≥ T (tested). 'flat' positions sit in cash (0 return). *Why:* simple, conservative,
   provably leak-free, and deterministic.

5. **Asset ranking uses 24h dollar-volume, not market cap.** Point-in-time market-cap universe
   membership is not implemented. `rank_by: market_cap` is therefore rejected rather than silently
   approximated; the flagship uses volume_24h / breadth.

6. **Flagship reported honestly, not curve-fit.** The backtest window happened to be a severe
   bear market (BTC −45%). Regime Pilot returned −10.4% — a +34.6pp outperformance with a 12.4%
   max drawdown — by routing to cash (the `chop`/`crowded_fragile` flat playbooks) through the
   decline. We deliberately did NOT tune parameters to flip the absolute return positive; that
   would be the exact overfitting the falsification report and on-chain attestation are built to
   expose. The honest value proposition is capital preservation / defensive regime routing,
   stress-tested out-of-sample by the falsification suite.

7. **The attested record is MAINNET only.** The production contract and commits use BSC mainnet,
   and x402 settlement uses Base mainnet. In-memory EVM and optional testnet paths are verification
   tools only and never contribute to the attested record.

8. **CMC Pro remains a shadow source until a versioned cutover.** Hourly access was verified on
   2026-06-19 and a 364-day cache was built for all 15 assets. Activating it requires a new
   strategy/data version, explicit cutover hour, source metadata, and refreshed reports.

9. **Re-froze live attestation from v1 to v2 (long/short) on 2026-06-13 ~11:26 UTC.** v2 adds
    disciplined short exposure (short only confirmed downtrends — breadth breakdown AND price below
    30d trend AND vol not extreme; never fades euphoria or shorts into capitulation; 20 bps/day
    borrow cost). v2 tested better OUT-OF-SAMPLE (embargo +1.8% vs v1 +0.4%, Sharpe 2.98 vs 2.21,
    walk-forward +1.3% vs +0.2%), shuffle-clean, robust — and its deflated Sharpe did NOT improve
    (0.013), confirming no overfitting (neither version has a statistically significant edge over
    the full bear window; the live forward test is the arbiter). Thresholds set by economic logic /
    symmetry, not search, so trials stay 27. Engineering: v1 spec file untouched; `attest/verify.py`
    and `reveal.py` match each commit to whichever spec reproduces its on-chain hash, so commits 0-3
    (v1) stay verifiable while 4+ are v2. `commit_hour.py` now points at v2. v1 remains the
    documented fallback (operator's call: revert by repointing commit_hour to v1).

10. **Solidity toolchain = `py-solc-x` + `web3.py`.**
   *Why:* one language and one dependency set keep contract compilation and interaction
   reproducible.
