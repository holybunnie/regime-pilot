#!/usr/bin/env python3
"""Regenerate all demo assets offline from the local cache (< 5 min, no network).

Produces in demo/:
  - equity_v1_v2_vs_btc.png   normalized equity: v1 (long-only), v2 (long/short), BTC buy&hold
  - regime_timeline_v2.png    v2 regime over time
  - bundles the key reports (falsification, data plan, on-chain verification)
  - RUNBOOK.md                the three-minute judge demo script

Run: python demo/build_demo.py   (or: make demo)
"""
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import pandas as pd                      # noqa: E402

REPO = Path(__file__).resolve().parent.parent

DEMO = REPO / "demo"
V1_REPORT = REPO / "engine" / "reports" / "regime_pilot"
V2_REPORT = REPO / "engine" / "reports" / "v2"


def equity_series(report_dir):
    report_dir = Path(report_dir)
    eq = pd.read_csv(report_dir / "equity_curve.csv")
    eq["ts"] = pd.to_datetime(eq["ts"], utc=True)
    summary = json.loads((report_dir / "summary.json").read_text())
    return eq.set_index("ts"), summary


def main():
    DEMO.mkdir(exist_ok=True)
    print("Rendering charts from frozen published v1 and v2 reports...")
    e1, s1 = equity_series(V1_REPORT)
    e2, s2 = equity_series(V2_REPORT)

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

    with (REPO / "attest" / "commits_public.csv").open() as handle:
        public_rows = list(csv.DictReader(handle))
    primary_count = len(public_rows)
    first_hour = datetime.fromisoformat(public_rows[0]["timestamp_utc"].replace("Z", "+00:00"))
    last_hour = datetime.fromisoformat(public_rows[-1]["timestamp_utc"].replace("Z", "+00:00"))
    expected_hours = int((last_hour - first_hour).total_seconds() / 3600) + 1
    missing_hours = expected_hours - primary_count
    coverage = primary_count / expected_hours
    coverage_end = last_hour.strftime("%B %-d at %H:%M UTC")

    # --- runbook ---
    (DEMO / "RUNBOOK.md").write_text(f"""# Demo Runbook

All assets here regenerate offline via `make demo` (< 5 min) from frozen published reports, the
committed ledger snapshot, and the local BTC cache.

## Three-minute walkthrough

### 0:00–0:25 — Problem and claim

Show the README title.

“AI can produce unlimited plausible backtests. The hard problem is proving which results deserve
trust. Regime Pilot turns natural-language intent into a closed strategy spec, then measures it
with deterministic execution, adversarial falsification, and an on-chain forward record.”

### 0:25–0:55 — Intent becomes measurable

Show `skill/examples/regime_pilot.intent.md`, then `spec/regime_pilot_v2.spec.json`.

“The LLM stops here. It authors a schema-validated JSON spec; it never touches prices, execution,
or results. From this file onward, the same inputs produce the same outputs. `make verify` checks
that boundary offline on a clean machine.”

### 0:55–1:40 — The honest result

Show `equity_v1_v2_vs_btc.png`, then `falsify__REPORT_regime_pilot_v2.spec.md`.

“Here is the result most strategy demos would hide. The historical backtest covers September 16,
2025 through June 13, 2026; 2025 is the start of the tested data, not the report date. In that
frozen window, v1 returned minus 10.4 percent and v2 minus 10.9 percent while BTC fell 44.7
percent. That is defensive capital preservation, not statistically significant alpha.
Walk-forward folds were negative, and after penalizing 27 trials the deflated Sharpe is 0.013.
The favorable 1.8 percent slice is shown only after the full-window result because it is one small
out-of-sample window.”

“Our own verifier told us our own strategy has no demonstrated directional edge. That is the
product working. A verifier that only says yes when its creators want yes is worthless.”

### 1:40–2:30 — Proof that cannot be backdated

Show the BscScan contract, one old transaction, then `attest__VERIFICATION.md`.

“Each decision-hour signal is reduced to a hash and committed to BNB Smart Chain before that
hour’s outcome. The block timestamp is the chain’s clock, not ours. The current public ledger has
{primary_count} primary predictions; two duplicate transactions are disclosed as ids 7 and 26,
and {missing_hours} decision hours are missing, for {coverage:.1%} coverage through {coverage_end}.
Nothing is silently dropped: the verifier starts from the contract’s own commit count.”

“Before reveal, this proves existence, ordering, timing, and complete accounting while payloads
remain sealed. After reveal, `make attest-verify` also recomputes each payload and salt against its
on-chain hash.”

### 2:30–3:00 — Reproducibility and close

Show the `make verify` result, then `x402plan__DATA_PLAN.md`.

“Thirteen offline gates and seventeen tests pass. The data plan also records a real one-cent USDC
x402 payment and reports economics net of measured data cost.”

“Regime Pilot is not a promise of future profit. It is a filter for AI-generated strategies:
closed specification, deterministic measurement, active attempts to disprove the edge, and a
forward record that cannot be rewritten after the outcome. Three commands reproduce the evidence:
`make verify`, `make demo`, and `make attest-verify`.”

*Backtested/forward performance does not predict future results. Zero trades executed.*
""")
    print(f"Demo assets written to {DEMO}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
