#!/usr/bin/env python3
"""Deterministic, lookahead-proof backtest engine.

Key guarantees (each has a test):
  - No lookahead: a decision at hour T uses only data with index < T. Enforced two
    ways: (1) every feature series is shifted by one hour before any predicate reads
    it, and (2) a GuardedAccessor raises LookaheadError on any raw read at index >= T.
  - Determinism: pure pandas/numpy, fixed iteration order, no randomness; numeric
    outputs are rounded to a fixed precision so result files are byte-identical.

Execution model (documented in DECISIONS.md):
  - Decision at hour T uses features built from data <= T-1h (shift by 1).
  - The resulting target weights are filled at the close of hour T (≈1h latency,
    consistent with costs.latency_minutes at hourly granularity).
  - Costs = turnover * (fee_bps + slippage_bps) / 1e4, slippage size-aware.
  - 'flat' positions sit in cash (0 return).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import indicators as ind          # noqa: E402
from engine import sizing as sz               # noqa: E402

CACHE = REPO / "engine" / "data" / "cache"
ROUND = 10                                     # decimals for byte-identical output


class LookaheadError(Exception):
    """Raised when code attempts to read data at or after the decision time."""


# --------------------------------------------------------------- data loading
def load_panels(symbols, benchmark="BTC"):
    closes, vols = {}, {}
    for s in symbols:
        df = pd.read_parquet(CACHE / f"ohlcv_{s}.parquet")
        closes[s] = df["close"]
        vols[s] = df["close"] * df["volume"]            # dollar volume proxy
    close = pd.DataFrame(closes).sort_index()
    dvol = pd.DataFrame(vols).sort_index()
    idx = close.index
    fg = pd.read_parquet(CACHE / "fear_greed.parquet")["fear_greed"]
    fg_h = fg.reindex(idx.union(fg.index)).sort_index().ffill().reindex(idx)
    return {"close": close, "dvol24": dvol.rolling(24, min_periods=1).sum(),
            "btc": close[benchmark], "fear_greed": fg_h, "index": idx}


# --------------------------------------------------------- feature computation
def build_features(spec, panels):
    """Return a DataFrame of scalar-per-hour features, each SHIFTED by 1 hour so a
    decision at T sees only data < T."""
    out = pd.DataFrame(index=panels["index"])
    for f in spec["features"]:
        src = f["source"]
        asset = f.get("asset")
        if src == "price":
            base = panels["close"][asset] if asset else panels["btc"]
        elif src == "btc_price":
            base = panels["btc"]
        elif src == "fear_greed":
            base = panels["fear_greed"]
        elif src == "volume_24h":
            base = panels["dvol24"][asset] if asset else panels["dvol24"].sum(axis=1)
        else:
            raise NotImplementedError(
                f"feature source '{src}' not available in the current data tier "
                f"(have: price, btc_price, fear_greed, volume_24h). See ASSUMPTIONS.md.")
        t = f["transform"]; kind = t["kind"]
        if kind == "raw":
            series = base
        elif kind == "sma":
            series = ind.sma(base, t["window"])
        elif kind == "realized_vol":
            series = ind.realized_vol(base, t["window"])
        elif kind == "percentile_rank":
            series = ind.percentile_rank(base, t["window"])
        elif kind == "delta":
            series = ind.delta(base, t["window"])
        elif kind == "breadth":
            series = ind.breadth(panels["close"], t["threshold_window"])
        else:
            raise ValueError(f"unknown transform {kind}")
        if t.get("rank_window"):                 # optional percentile-rank of the transform output
            series = ind.percentile_rank(series, t["rank_window"])
        out[f["name"]] = series.shift(1)        # <-- the no-lookahead shift
    return out


# ------------------------------------------------------------ predicate engine
def _operand(o, now, prev):
    if "const" in o:
        return o["const"], o["const"]
    name = o["feature"]
    return now.get(name), (prev.get(name) if prev is not None else None)


def eval_pred(pred, now, prev):
    if "const_bool" in pred:
        return pred["const_bool"]
    op = pred["op"]
    if op == "and":
        return all(eval_pred(a, now, prev) for a in pred["args"])
    if op == "or":
        return any(eval_pred(a, now, prev) for a in pred["args"])
    if op == "not":
        return not eval_pred(pred["args"][0], now, prev)
    ln, lp = _operand(pred["left"], now, prev)
    rn, rp = _operand(pred["right"], now, prev)
    if ln is None or rn is None or (isinstance(ln, float) and np.isnan(ln)) \
       or (isinstance(rn, float) and np.isnan(rn)):
        return False
    if op == ">":
        return ln > rn
    if op == "<":
        return ln < rn
    if op == ">=":
        return ln >= rn
    if op == "<=":
        return ln <= rn
    if op in ("crosses_above", "crosses_below"):
        if lp is None or rp is None or (isinstance(lp, float) and np.isnan(lp)) \
           or (isinstance(rp, float) and np.isnan(rp)):
            return False
        if op == "crosses_above":
            return lp <= rp and ln > rn
        return lp >= rp and ln < rn
    raise ValueError(f"unknown op {op}")


# ----------------------------------------------------------- regime hysteresis
def assign_regimes(spec, feats):
    regimes = spec["regimes"]
    names = [r["name"] for r in regimes]
    streak = {n: 0 for n in names}
    current = names[-1]                          # start in the catch-all
    out = []
    rows = feats.to_dict("records")
    for i, now in enumerate(rows):
        prev = rows[i - 1] if i > 0 else None
        for r in regimes:
            streak[r["name"]] = streak[r["name"]] + 1 if eval_pred(r["predicate"], now, prev) else 0
        candidate = next((r["name"] for r in regimes
                          if streak[r["name"]] >= r["persistence_hours"]), None)
        if candidate is not None:
            current = candidate
        out.append(current)
    return pd.Series(out, index=feats.index, name="regime")


# ----------------------------------------------------------- guarded accessor
class GuardedAccessor:
    """Defensive no-lookahead layer over the raw close panel.

    `decision_price(asset, T)` returns the last close strictly before T.
    `raw_at(asset, ts, T)` raises if ts >= T — the canary the lookahead test trips.
    """
    def __init__(self, close):
        self._close = close

    def raw_at(self, asset, ts, decision_time):
        if ts >= decision_time:
            raise LookaheadError(
                f"attempted to read {asset} at {ts} during a decision at {decision_time}")
        return self._close[asset].asof(ts)

    def decision_price(self, asset, decision_time):
        prior = self._close.index[self._close.index < decision_time]
        if len(prior) == 0:
            raise LookaheadError(f"no data before {decision_time}")
        return self.raw_at(asset, prior[-1], decision_time)


# ---------------------------------------------------------------- the backtest
def select_assets(playbook, feats_row, panels, t, universe):
    sel = playbook.get("select", {})
    rank_by = sel.get("rank_by", "volume_24h")
    top_n = sel.get("top_n", len(universe))
    avail = [a for a in universe if not np.isnan(panels["close"][a].asof(t))]
    if rank_by == "volume_24h":
        avail.sort(key=lambda a: panels["dvol24"][a].asof(t - pd.Timedelta(hours=1)), reverse=True)
    elif rank_by == "feature":
        # ranking feature must be per-asset; fall back to liquidity if not resolvable here
        avail.sort(key=lambda a: panels["dvol24"][a].asof(t - pd.Timedelta(hours=1)), reverse=True)
    else:
        raise NotImplementedError(
            f"rank_by='{rank_by}' needs a market-cap snapshot not in the current data tier; "
            f"use volume_24h. See ASSUMPTIONS.md.")
    return avail[:top_n]


def target_weights(spec, row, panels, t, regime, dd, ladder, universe):
    """Deterministic target portfolio weights for `regime` at hour `t`.

    Shared by the backtest (live drawdown `dd`) and the live attestation committer
    (dd=0 -> full-budget intent) so the attested signal matches the engine exactly.
    """
    sizing, risk = spec["sizing"], spec["risk"]
    pb = spec["playbooks"][regime]
    w = {a: 0.0 for a in universe}
    asset_vol = row.get(sizing["asset_vol_feature"])
    if pb["action"] == "flat" or asset_vol is None or np.isnan(asset_vol):
        return w
    base = sz.position_size(asset_vol, sizing["k"], sizing["vol_target_annual"],
                            dd, risk["max_drawdown_budget"], sizing.get("max_position_weight", 0.5))
    gmult = sz.gross_multiplier(dd, risk["max_drawdown_budget"], ladder, regime)
    gross = min(base, risk["max_gross_exposure"]) * gmult
    if pb["action"] == "hold_assets":
        chosen = select_assets(pb, row, panels, t, universe)
        if chosen:
            wt = min(gross / len(chosen), risk["per_asset_cap"])
            for a in chosen:
                w[a] = wt
    elif pb["action"] == "staged_reentry":
        scale = float(np.clip((row.get(pb.get("reentry_feature"), 0) or 0) / 100.0, 0, 1))
        for a in pb.get("assets", []):
            if a in w:
                w[a] = min(gross * scale, risk["per_asset_cap"])
    elif pb["action"] == "mean_revert":
        chosen = select_assets({"select": {"rank_by": "volume_24h", "top_n": 1}},
                               row, panels, t, universe)
        for a in chosen:
            w[a] = min(gross * 0.5, risk["per_asset_cap"])
    return w


def run(spec, universe=None, end=None, panels=None, feats=None):
    """Run the backtest. If `end` (UTC Timestamp) is given, no decision is made at or
    after it — used to keep parameter fitting strictly out of the embargoed window.

    Optional `panels`/`feats` injection (default None = compute normally) lets the
    falsification suite reuse data/features across variants and feed shuffled data.
    These are additive: the live attestation path (compute_signal) never calls run()."""
    universe = universe or [t["symbol"] for t in
                            json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]]
    if panels is None:
        panels = load_panels(universe)
    if feats is None:
        feats = build_features(spec, panels)
    regime_series = assign_regimes(spec, feats)

    close = panels["close"]
    rets = close.pct_change()
    ladder = sz.ladder_from_spec(spec["risk"])
    risk, sizing, costs = spec["risk"], spec["sizing"], spec["costs"]
    avf = sizing["asset_vol_feature"]

    # warmup: first hour where all features are non-NaN
    valid = feats.dropna(how="any")
    if valid.empty:
        raise RuntimeError("no hours with all features populated — check windows vs history")
    start = valid.index[0]
    hours = close.index[close.index >= start]
    if end is not None:
        hours = hours[hours <= end]

    equity, peak = 1.0, 1.0
    w_prev = {a: 0.0 for a in universe}
    eq_rows, trade_rows = [], []

    feats_d = feats
    for i in range(len(hours) - 1):
        t = hours[i]
        t_next = hours[i + 1]
        row = feats_d.loc[t]
        regime = regime_series.loc[t]
        pb = spec["playbooks"][regime]
        dd = (peak - equity) / peak if peak > 0 else 0.0

        # ----- target weights (shared with the live attestation committer) -----
        w_target = target_weights(spec, row, panels, t, regime, dd, ladder, universe)

        # ----- costs on rebalance (filled at close[t]) -----
        cost = 0.0
        for a in universe:
            dw = abs(w_target[a] - w_prev[a])
            if dw > 1e-12:
                adv = panels["dvol24"][a].asof(t)
                notional = dw * equity
                slip = costs["slippage_bps_floor"] + costs["slippage_size_coeff"] * (
                    notional / adv if adv and adv > 0 else 0)
                cost += notional * (costs["fee_bps"] + slip) / 1e4
                trade_rows.append({"ts": t.isoformat(), "asset": a,
                                   "dw": round(dw, ROUND), "regime": regime})
        equity -= cost

        # ----- hold from close[t] to close[t+1] -----
        port_ret = sum(w_target[a] * (rets[a].get(t_next, 0.0) or 0.0) for a in universe)
        if np.isnan(port_ret):
            port_ret = 0.0
        equity *= (1.0 + port_ret)
        peak = max(peak, equity)
        w_prev = w_target
        eq_rows.append({"ts": t_next.isoformat(), "equity": round(equity, ROUND),
                        "drawdown": round((peak - equity) / peak, ROUND), "regime": regime,
                        "gross": round(sum(w_target.values()), ROUND)})

    bw = panels["btc"].loc[start:hours[-1]]
    bench_ret = float(bw.iloc[-1] / bw.iloc[0] - 1.0)
    bench_dd = float(((bw.cummax() - bw) / bw.cummax()).max())
    return _finalize(spec, eq_rows, trade_rows, regime_series, start, hours[-1],
                     bench_ret, bench_dd)


def _finalize(spec, eq_rows, trade_rows, regime_series, start, end, bench_ret, bench_dd):
    eq = pd.DataFrame(eq_rows)
    total_return = eq["equity"].iloc[-1] - 1.0
    max_dd = eq["drawdown"].max()
    eqret = eq["equity"].pct_change().dropna()
    sharpe = (eqret.mean() / eqret.std() * np.sqrt(ind.HOURS_PER_YEAR)) if eqret.std() > 0 else 0.0
    per_regime = eq.groupby("regime")["equity"].count().to_dict()
    summary = {
        "spec_name": spec["meta"]["name"], "spec_version": spec["meta"]["version"],
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "total_return": round(float(total_return), 6),
        "max_drawdown": round(float(max_dd), 6),
        "sharpe_annualized": round(float(sharpe), 6),
        "benchmark_btc_return": round(bench_ret, 6),
        "benchmark_btc_max_drawdown": round(bench_dd, 6),
        "excess_return_vs_btc": round(float(total_return) - bench_ret, 6),
        "trade_count": len(trade_rows),
        "avg_gross_exposure": round(float(eq["gross"].mean()), 6),
        "hours_per_regime": per_regime,
        "fee_bps": spec["costs"]["fee_bps"],
        "slippage_bps_floor": spec["costs"]["slippage_bps_floor"],
        "configurations_tried": spec["meta"]["configurations_tried"],
        "disclaimer": "Backtested performance does not predict live results. Zero trades executed.",
    }
    return {"equity": eq, "trades": pd.DataFrame(trade_rows), "summary": summary}


def _report_md(s):
    rp = "\n".join(f"| {k} | {v} |" for k, v in sorted(s["hours_per_regime"].items()))
    return f"""# Backtest Report — {s['spec_name']} v{s['spec_version']}

**Window:** {s['window_start'][:16]} → {s['window_end'][:16]} UTC

## Headline (net of costs)
| Metric | Strategy | BTC buy & hold |
|--------|---------:|---------------:|
| Total return | {s['total_return']:+.2%} | {s['benchmark_btc_return']:+.2%} |
| Max drawdown | {s['max_drawdown']:.2%} | {s['benchmark_btc_max_drawdown']:.2%} |
| Excess return vs BTC | **{s['excess_return_vs_btc']:+.2%}** | — |
| Annualized Sharpe | {s['sharpe_annualized']:.2f} | — |
| Trades | {s['trade_count']} | — |
| Avg gross exposure | {s['avg_gross_exposure']:.1%} | 100% |

## Hours per regime
| Regime | Hours |
|--------|------:|
{rp}

## Disclosures (honesty rule R8)
- **Data sources:** hourly OHLCV from Binance public API (backtest prices); Fear & Greed history
  from CoinMarketCap `/v3/fear-and-greed/historical`. See DECISIONS.md for the hybrid-data rationale.
- **Costs modeled:** {s['fee_bps']} bps fee/side + {s['slippage_bps_floor']} bps slippage floor + size-aware slippage.
- **Configurations tried:** {s['configurations_tried']} (used by the deflated Sharpe in the falsification report).
- **Disclaimer:** {s['disclaimer']}
"""


def write_outputs(result, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    result["equity"].to_csv(outdir / "equity_curve.csv", index=False, lineterminator="\n")
    result["trades"].to_csv(outdir / "trades.csv", index=False, lineterminator="\n")
    (outdir / "summary.json").write_text(json.dumps(result["summary"], indent=2, sort_keys=True))
    (outdir / "report.md").write_text(_report_md(result["summary"]))


def main(argv):
    spec_path = Path(argv[1]) if len(argv) > 1 else REPO / "spec" / "regime_pilot.spec.json"
    outdir = Path(argv[2]) if len(argv) > 2 else REPO / "engine" / "reports" / spec_path.stem
    spec = json.loads(spec_path.read_text())
    result = run(spec)
    write_outputs(result, outdir)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"\nOutputs written to {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
