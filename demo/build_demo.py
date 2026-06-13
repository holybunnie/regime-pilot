#!/usr/bin/env python3
"""Regenerate all demo assets offline from the local cache (< 5 min, no network).

Produces in demo/:
  - equity_v1_v2_vs_btc.png   normalized equity: v1 (long-only), v2 (long/short), BTC buy&hold
  - regime_timeline_v2.png    v2 regime over time
  - bundles the key reports (falsification, data plan, on-chain verification)
  - RUNBOOK.md                the demo script

Run: python demo/build_demo.py   (or: make demo)
"""
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import pandas as pd                      # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt        # noqa: E402

DEMO = REPO / "demo"
V1 = REPO / "spec" / "regime_pilot.spec.json"
V2 = REPO / "spec" / "regime_pilot_v2.spec.json"


def equity_series(spec_path):
    res = bt.run(json.loads(Path(spec_path).read_text()))
    eq = res["equity"].copy()
    eq["ts"] = pd.to_datetime(eq["ts"], utc=True)
    return eq.set_index("ts"), res["summary"]


def main():
    DEMO.mkdir(exist_ok=True)
    print("Running v1 and v2 backtests from cache...")
    e1, s1 = equity_series(V1)
    e2, s2 = equity_series(V2)

    # BTC buy & hold over the common window
    btc = pd.read_parquet(REPO / "engine" / "data" / "cache" / "ohlcv_BTC.parquet")["close"]
    start = max(e1.index.min(), e2.index.min())
    end = min(e1.index.max(), e2.index.max())
    bw = btc.loc[start:end]
    bw = bw / bw.iloc[0]

    # --- chart 1: equity curves ---
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(e1.index, e1["equity"], label=f"v1 long-only ({s1['total_return']:+.1%})", lw=1.6)
    ax.plot(e2.index, e2["equity"], label=f"v2 long/short ({s2['total_return']:+.1%})", lw=1.6)
    ax.plot(bw.index, bw.values, label=f"BTC buy&hold ({bw.iloc[-1]-1:+.1%})", lw=1.2, ls="--", color="gray")
    ax.set_title("Regime Pilot — equity vs BTC (bear-market window)")
    ax.set_ylabel("growth of $1"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(DEMO / "equity_v1_v2_vs_btc.png", dpi=120); plt.close(fig)

    # --- chart 2: v2 regime timeline ---
    regimes = list(dict.fromkeys(e2["regime"]))
    rmap = {r: i for i, r in enumerate(regimes)}
    fig, ax = plt.subplots(figsize=(10, 2.6))
    ax.scatter(e2.index, e2["regime"].map(rmap), s=2)
    ax.set_yticks(range(len(regimes))); ax.set_yticklabels(regimes)
    ax.set_title("v2 regime over time"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(DEMO / "regime_timeline_v2.png", dpi=120); plt.close(fig)

    # --- bundle key reports ---
    for src in ["falsify/REPORT.md", "falsify/REPORT_regime_pilot_v2.spec.md",
                "x402plan/DATA_PLAN.md", "attest/VERIFICATION.md",
                "engine/reports/regime_pilot/report.md"]:
        p = REPO / src
        if p.exists():
            shutil.copy(p, DEMO / (src.replace("/", "__")))

    # --- runbook ---
    (DEMO / "RUNBOOK.md").write_text(f"""# Demo Runbook

All assets here regenerate offline via `make demo` (< 5 min, from the local cache).

## 90-second walkthrough
1. **Equity** — `equity_v1_v2_vs_btc.png`: in a market that fell {bw.iloc[-1]-1:+.0%}, v1 preserved
   capital ({s1['total_return']:+.1%}) and v2 ({s2['total_return']:+.1%}) added a disciplined short.
2. **Regimes** — `regime_timeline_v2.png`: the router moving between trend-up / downtrend /
   capitulation / chop.
3. **Honesty** — open `falsify__REPORT_regime_pilot_v2.spec.md`: shuffle canary passed, robust,
   deflated Sharpe stated plainly (~0.01 — no overstated edge).
4. **The differentiator** — `attest__VERIFICATION.md`: every hourly signal hash committed on BSC
   mainnet BEFORE its outcome, all independently reproduced. Contract:
   https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1
5. **x402** — `x402plan__DATA_PLAN.md`: a real $0.01 USDC request paid on Base, net-of-cost economics.

*Backtested/forward performance does not predict future results. Zero trades executed.*
""")
    print(f"Demo assets written to {DEMO}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
