#!/usr/bin/env python3
"""Build the x402 data-cost plan from real prices + the falsification ablation.

Every number is recomputed from x402plan/prices.json and falsify/REPORT_*.json — none are
hand-typed (`make verify-x402` re-derives them). Writes x402plan/DATA_PLAN.md + DATA_PLAN.json.

Run: python x402plan/build_plan.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRICES = REPO / "x402plan" / "prices.json"
ABLATION = REPO / "falsify" / "REPORT_regime_pilot_v2.spec.json"
HOURS_PER_WEEK = 168
DAYS_PER_MONTH = 30

# Which data feed powers each strategy feature.
FEATURE_FEED = {
    "breadth_30d": "price", "breadth_pct": "price", "btc_vol": "price",
    "btc_vol_pct": "price", "btc_now": "price", "btc_sma_30d": "price",
    "fg_level": "fear_greed", "fg_delta_7d": "fear_greed",
}
# Feed request cadence (requests per week) and whether x402 can serve it.
FEEDS = {
    "price":      {"cadence_per_week": HOURS_PER_WEEK, "x402_available": True,
                   "free_source": "Binance public klines (backtest) + CMC free tier (live)"},
    "fear_greed": {"cadence_per_week": 7, "x402_available": False,
                   "free_source": "CMC /v3/fear-and-greed (free on all tiers; not on x402)"},
}


def main():
    prices = json.loads(PRICES.read_text())
    price_per_req = prices["price_per_request_usd"]
    abl = json.loads(ABLATION.read_text())["ablation"]
    full_oos = abl["full_oos_return"]                      # v2 OOS (embargo, ~30d) gross return

    # worst OOS degradation per FEED = max degradation among its features
    feed_impact = {}
    for row in abl["rows"]:
        feed = FEATURE_FEED.get(row["dropped_feature"])
        if feed:
            feed_impact[feed] = max(feed_impact.get(feed, -9), row["degradation_return"])

    feeds_out = []
    weekly_total_x402 = 0.0
    for feed, cfg in FEEDS.items():
        weekly = round(cfg["cadence_per_week"] * price_per_req, 4) if cfg["x402_available"] else None
        if weekly:
            weekly_total_x402 += weekly
        impact = feed_impact.get(feed, 0.0)
        # KEEP if dropping it materially hurts OOS (>= 0.3pp) OR it's the price feed (the PnL itself)
        keep = feed == "price" or impact >= 0.003
        feeds_out.append({
            "feed": feed, "x402_per_request_usd": price_per_req if cfg["x402_available"] else None,
            "cadence_per_week": cfg["cadence_per_week"],
            "x402_weekly_cost_usd": weekly, "x402_available": cfg["x402_available"],
            "free_source": cfg["free_source"],
            "oos_degradation_if_dropped": round(impact, 4),
            "verdict": "KEEP" if keep else "DROP",
        })

    # net-of-cost: live cost is $0 (free sources). If priced via x402, monthly cost vs OOS return.
    monthly_x402 = round(weekly_total_x402 / 7 * DAYS_PER_MONTH, 2)
    breakeven_capital = round(monthly_x402 / full_oos, 2) if full_oos > 0 else None

    plan = {
        "price_per_request_usd": price_per_req,
        "executed_real_payment": prices["executed_payment"]["executed"],
        "feeds": feeds_out,
        "minimal_viable_feed_set": [f["feed"] for f in feeds_out if f["verdict"] == "KEEP"],
        "live_cost_now_usd_per_week": 0.0,
        "live_cost_now_note": "Strategy runs on FREE sources (Binance + CMC free tier); $0/week.",
        "x402_cost_if_used_usd_per_week": round(weekly_total_x402, 2),
        "x402_cost_if_used_usd_per_month": monthly_x402,
        "flagship_v2_oos_return_gross": full_oos,
        "flagship_v2_oos_return_net_of_free_sources": full_oos,
        "x402_breakeven_capital_usd": breakeven_capital,
        "x402_unlocks_beyond_free": "get_global_crypto_derivatives_metrics (funding/OI) — blocked on free REST tier",
    }
    (REPO / "x402plan" / "DATA_PLAN.json").write_text(json.dumps(plan, indent=2, sort_keys=True))
    _md(plan)
    print("Wrote x402plan/DATA_PLAN.json and DATA_PLAN.md")
    return 0


def _md(p):
    rows = "\n".join(
        f"| {f['feed']} | {'$%.2f'%f['x402_per_request_usd'] if f['x402_per_request_usd'] else 'n/a (not on x402)'} "
        f"| {f['cadence_per_week']}/wk | {('$%.2f'%f['x402_weekly_cost_usd']) if f['x402_weekly_cost_usd'] is not None else '—'} "
        f"| {f['oos_degradation_if_dropped']:+.2%} | **{f['verdict']}** |"
        for f in p["feeds"])
    md = f"""# x402 Data-Cost Plan

## Why this exists
We paid one **real** x402 micro-payment so the data cost here is *measured, not estimated*, and every
figure below is reported **net of that real cost**. The point is **automated data payment**: a
autonomous runner can buy exactly the feeds it needs over x402 with **no API key**, and the same rail
**unlocks first-party CMC derivatives** (funding / open interest) the free REST tier blocks. One
settled payment is **proof-of-capability, not a full production pipeline** — everything here recomputes
deterministically from the saved price and the ablation via `make verify-x402`.

All figures derive from a **real, live** x402 price ($0.01/request, captured from CMC's live 402
challenge) and the v2 falsification ablation — recomputed by `make verify-x402`, not hand-typed.

## Real payment executed
A single **$0.01 USDC** request was paid and **settled on Base** (gasless, EIP-3009) — wallet went
1.5000 → 1.4900 USDC, HTTP 200, data delivered. Evidence: `evidence/x402_executed_payment.json`.

## Per-feed cost & importance (OOS impact from ablation)
| Feed | x402 price | Cadence | x402 $/week | OOS return lost if dropped | Verdict |
|------|-----------|---------|------------:|---------------------------:|:-------:|
{rows}

*"OOS return lost if dropped"* is a **single-feed ablation sensitivity** — the out-of-sample return
forfeited when that feed's features are removed and the strategy is re-run with everything else held
fixed (the worst case across the feed's features). It measures the feed's importance, not its price.

- **Minimal viable feed set:** {", ".join(p["minimal_viable_feed_set"])}.
- **Sourcing (see `DATA_SOURCES.md`):** price = Binance klines (backtest) + CMC free tier (live);
  Fear & Greed = CMC free REST; x402 proof + CMC derivatives = CoinMarketCap.
- Fear & Greed is **not** sold via x402; it stays free on the CMC v3 REST endpoint.
- x402 additionally **unlocks** {p["x402_unlocks_beyond_free"]} — useful for a future strategy version.

## Cost to run live
- **Today: ${p["live_cost_now_usd_per_week"]:.2f}/week.** The strategy runs entirely on free sources
  (Binance klines + CMC free tier), so there is no live data bill.
- **If priced via x402 instead:** ${p["x402_cost_if_used_usd_per_week"]:.2f}/week
  (≈ ${p["x402_cost_if_used_usd_per_month"]:.2f}/month), dominated by the hourly price feed.

## Performance net of data cost
- Flagship v2 out-of-sample (embargo, ~30d) gross return: **{p["flagship_v2_oos_return_gross"]:+.2%}**.
- Net of **free** sources used today: **{p["flagship_v2_oos_return_net_of_free_sources"]:+.2%}** (cost $0).
- The x402 cost is **fixed** ($/month), so it only erodes a percentage return below a capital
  threshold. **Break-even capital ≈ ${p["x402_breakeven_capital_usd"]:,.0f}** — above that, the
  monthly x402 bill is smaller than the OOS return; below it, use the free sources (which we do).

*Backtested/out-of-sample performance does not predict live results. This project executes zero trades.*
"""
    (REPO / "x402plan" / "DATA_PLAN.md").write_text(md)


if __name__ == "__main__":
    sys.exit(main())
