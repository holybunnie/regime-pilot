#!/usr/bin/env python3
"""Generate the falsification report: falsify/REPORT.md + falsify/REPORT.json.

Sections (per the build spec):
  1. Walk-forward      — params chosen only on past windows; embargo evaluated once, last.
  2. Perturbation      — every numeric threshold +/-20%; robust (smooth) vs fragile (cliff).
  3. Shuffled canary   — time-shuffle returns (fixed seed); the edge must vanish.
  4. Deflated Sharpe   — Bailey & Lopez de Prado, trials = meta.configurations_tried.
  5. Feature ablation  — drop each feature (neutralize its predicates); report degradation.
  + plain-English executive summary with the standing disclaimer.

Efficiency: features are computed ONCE and injected into every variant run (grid,
perturbation, ablation share identical features); only the shuffle canary recomputes.
The frozen spec/universe on disk are never modified.

Run: python falsify/report.py   (or: make falsify)
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt          # noqa: E402
from engine import indicators as ind       # noqa: E402
from falsify import grid as G              # noqa: E402
from falsify import deflated_sharpe as DS  # noqa: E402

SPEC = REPO / "spec" / "regime_pilot.spec.json"
CACHE = REPO / "engine" / "data" / "cache"
SEED = 20260613

HPY = ind.HOURS_PER_YEAR


def metrics(eq, start=None, end=None):
    """Performance metrics on an equity DataFrame, optionally sliced to [start,end]."""
    df = eq.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    if start is not None:
        df = df[df["ts"] >= start]
    if end is not None:
        df = df[df["ts"] < end]
    if len(df) < 3:
        return {"total_return": 0.0, "sharpe": 0.0, "max_dd": 0.0, "n": len(df)}
    e = df["equity"].values
    e = e / e[0]
    rets = np.diff(e) / e[:-1]
    peak = np.maximum.accumulate(e)
    sharpe = float(rets.mean() / rets.std() * np.sqrt(HPY)) if rets.std() > 0 else 0.0
    return {"total_return": float(e[-1] - 1), "sharpe": round(sharpe, 4),
            "max_dd": float(((peak - e) / peak).max()), "n": len(df),
            "per_period_sharpe": float(rets.mean() / rets.std()) if rets.std() > 0 else 0.0,
            "skew": float(pd.Series(rets).skew()), "kurt": float(pd.Series(rets).kurt() + 3.0)}


def load_base(spec_path=SPEC):
    spec = json.loads(Path(spec_path).read_text())
    universe = [t["symbol"] for t in json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]]
    panels = bt.load_panels(universe)
    feats = bt.build_features(spec, panels)
    manifest = json.loads((CACHE / "manifest.json").read_text())
    embargo = pd.Timestamp(manifest["embargo_start"])
    return spec, universe, panels, feats, embargo


def run_eq(spec, panels, feats):
    return bt.run(spec, panels=panels, feats=feats)["equity"]


# ---------------------------------------------------------------- 1. walk-forward
def walk_forward(base, panels, feats, embargo, folds=5):
    configs = list(G.grid(base))
    eqs = {label: run_eq(spec, panels, feats) for label, spec in configs}
    any_eq = next(iter(eqs.values()))
    ts = pd.to_datetime(any_eq["ts"], utc=True)
    pre = ts[ts < embargo]
    if len(pre) < folds + 2:
        return {"error": "insufficient pre-embargo history"}
    edges = pd.to_datetime(np.linspace(pre.iloc[0].value, pre.iloc[-1].value, folds + 1)).tz_localize("UTC")
    out = []
    for i in range(1, folds):
        train_end = edges[i]
        val_end = edges[i + 1]
        # choose config by Sharpe on all data before the validation fold
        best = max(eqs, key=lambda c: metrics(eqs[c], end=train_end)["sharpe"])
        vm = metrics(eqs[best], start=train_end, end=val_end)
        out.append({"fold": i, "train_end": str(train_end)[:10], "val_end": str(val_end)[:10],
                    "selected": best, "val_sharpe": vm["sharpe"], "val_return": round(vm["total_return"], 4)})
    # embargo evaluated ONCE, last, with config chosen on all pre-embargo data
    best_final = max(eqs, key=lambda c: metrics(eqs[c], end=embargo)["sharpe"])
    em = metrics(eqs[best_final], start=embargo)
    return {"folds": out, "embargo_selected": best_final,
            "embargo_oos": {"sharpe": em["sharpe"], "return": round(em["total_return"], 4),
                            "max_dd": round(em["max_dd"], 4), "hours": em["n"]},
            "grid_sharpes": {c: metrics(e, end=embargo)["sharpe"] for c, e in eqs.items()}}


# ------------------------------------------------------------------ 2. perturbation
def perturb_specs(base):
    """One-at-a-time +/-20% on each numeric threshold."""
    specs = {}

    def add(label, mutate):
        s = copy.deepcopy(base)
        mutate(s)
        specs[label] = s

    for f in (0.8, 1.2):
        tag = "-20%" if f < 1 else "+20%"
        add(f"k {tag}", lambda s, f=f: s["sizing"].__setitem__("k", round(s["sizing"]["k"] * f, 4)))
        add(f"vol_target {tag}", lambda s, f=f: s["sizing"].__setitem__(
            "vol_target_annual", round(s["sizing"]["vol_target_annual"] * f, 4)))
        add(f"max_dd_budget {tag}", lambda s, f=f: s["risk"].__setitem__(
            "max_drawdown_budget", round(s["risk"]["max_drawdown_budget"] * f, 4)))

        add(f"fg_extremes {tag}", lambda s, f=f: (_scale_threshold_all(s, "fg_level", f)))
        add(f"vol_pct_thr {tag}", lambda s, f=f: (_scale_threshold_all(s, "btc_vol_pct", f)))
        add(f"breadth_thr {tag}", lambda s, f=f: (_scale_threshold_all(s, "breadth_pct", f)))
    return specs


def _scale_threshold(pred, feature, factor):
    if not isinstance(pred, dict):
        return
    if pred.get("op") in (">", "<", ">=", "<="):
        for side in ("left", "right"):
            other = "right" if side == "left" else "left"
            if pred.get(side, {}).get("feature") == feature and "const" in pred.get(other, {}):
                pred[other]["const"] = round(pred[other]["const"] * factor, 4)
    for a in pred.get("args", []):
        _scale_threshold(a, feature, factor)


def _scale_threshold_all(spec, feature, factor):
    for r in spec["regimes"]:
        _scale_threshold(r["predicate"], feature, factor)


def perturbation(base, panels, feats, embargo):
    baseline = metrics(run_eq(base, panels, feats), end=embargo)
    rows = []
    for label, spec in perturb_specs(base).items():
        m = metrics(run_eq(spec, panels, feats), end=embargo)
        rows.append({"param": label, "return": round(m["total_return"], 4),
                     "sharpe": m["sharpe"], "max_dd": round(m["max_dd"], 4),
                     "d_return": round(m["total_return"] - baseline["total_return"], 4)})
    swing = max(abs(r["d_return"]) for r in rows) if rows else 0.0
    return {"baseline_return": round(baseline["total_return"], 4),
            "baseline_sharpe": baseline["sharpe"], "rows": rows,
            "max_abs_return_swing": round(swing, 4),
            "verdict": "ROBUST (degrades smoothly)" if swing < 0.15 else "FRAGILE (results cliff)"}


# --------------------------------------------------------------- 3. shuffle canary
def shuffle_canary(base, panels, embargo, real_feats):
    rng = np.random.default_rng(SEED)
    close = panels["close"]
    rets = close.pct_change()
    shuffled_close = {}
    for col in close.columns:
        r = rets[col].dropna()
        perm = rng.permutation(r.values)
        s = pd.Series(perm, index=r.index)
        base_price = close[col].dropna().iloc[0]
        shuffled_close[col] = base_price * (1 + s).cumprod()
    sc = pd.DataFrame(shuffled_close).reindex(close.index)
    dvol = panels["dvol24"]  # keep liquidity ranking stable
    sp = {"close": sc, "dvol24": dvol, "btc": sc[panels["btc"].name],
          "fear_greed": panels["fear_greed"], "index": close.index}
    feats_shuf = bt.build_features(base, sp)
    real = metrics(run_eq(base, panels, real_feats), end=embargo)
    shuf = metrics(bt.run(base, panels=sp, feats=feats_shuf)["equity"], end=embargo)
    edge_survived = shuf["total_return"] > 0.05 and shuf["sharpe"] > 0.5
    return {"seed": SEED, "real_return": round(real["total_return"], 4), "real_sharpe": real["sharpe"],
            "shuffled_return": round(shuf["total_return"], 4), "shuffled_sharpe": shuf["sharpe"],
            "edge_survived_shuffle": edge_survived,
            "verdict": "LEAKAGE WARNING — edge survived shuffling!" if edge_survived
                       else "PASS — edge vanished on shuffled data (as it should)"}


# --------------------------------------------------------------- 4. deflated sharpe
def deflated(base, panels, feats, embargo, grid_sharpes):
    m = metrics(run_eq(base, panels, feats))  # full period
    sr = m["per_period_sharpe"]
    trial_sr = np.array(list(grid_sharpes.values())) / np.sqrt(HPY)  # de-annualize grid Sharpes
    var_sr = float(np.var(trial_sr, ddof=1))
    n = base["meta"]["configurations_tried"]
    dsr, sr_star = DS.deflated_sharpe(sr, m["n"], m["skew"], m["kurt"], var_sr, n)
    return {"observed_sharpe_annual": round(sr * np.sqrt(HPY), 4),
            "observed_sharpe_per_period": round(sr, 6), "n_obs": m["n"],
            "skew": round(m["skew"], 4), "kurt": round(m["kurt"], 4),
            "trials": n, "var_sr_trials": var_sr,
            "deflated_benchmark_sr_per_period": round(sr_star, 6),
            "deflated_sharpe_ratio": round(dsr, 4),
            "interpretation": ("clears the multiple-testing bar" if dsr > 0.95
                               else "does NOT clear the multiple-testing bar (likely no real edge)"),
            "reference": "Bailey & Lopez de Prado (2014), The Deflated Sharpe Ratio"}


# --------------------------------------------------------------- 5. feature ablation
def neutralize(pred, feature):
    """Replace any comparison referencing `feature` with const_bool:true (neutral in ANDs)."""
    if not isinstance(pred, dict):
        return pred
    if pred.get("op") in (">", "<", ">=", "<=", "crosses_above", "crosses_below"):
        if pred.get("left", {}).get("feature") == feature or pred.get("right", {}).get("feature") == feature:
            return {"const_bool": True}
    if "args" in pred:
        pred["args"] = [neutralize(a, feature) for a in pred["args"]]
    return pred


def ablation(base, panels, feats, embargo):
    full = metrics(run_eq(base, panels, feats), start=embargo)
    rows = []
    for f in base["features"]:
        name = f["name"]
        s = copy.deepcopy(base)
        for r in s["regimes"]:
            r["predicate"] = neutralize(r["predicate"], name)
        # ablated spec may change features only if it referenced a feature window; here we
        # only neutralize predicates, so features are unchanged -> reuse feats.
        m = metrics(run_eq(s, panels, feats), start=embargo)
        rows.append({"dropped_feature": name,
                     "oos_return": round(m["total_return"], 4), "oos_sharpe": m["sharpe"],
                     "degradation_return": round(full["total_return"] - m["total_return"], 4)})
    return {"full_oos_return": round(full["total_return"], 4), "full_oos_sharpe": full["sharpe"],
            "rows": rows}


# ----------------------------------------------------------------------- assemble
def main():
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SPEC
    suffix = "" if spec_path.stem == "regime_pilot" else "_" + spec_path.stem
    base, universe, panels, feats, embargo = load_base(spec_path)
    print(f"Falsifying {spec_path.name} ...")
    print("Running walk-forward (27 configs)...")
    wf = walk_forward(base, panels, feats, embargo)
    print("Running perturbation...")
    pt = perturbation(base, panels, feats, embargo)
    print("Running shuffle canary...")
    sc = shuffle_canary(base, panels, embargo, feats)
    print("Computing deflated Sharpe...")
    df = deflated(base, panels, feats, embargo, wf["grid_sharpes"])
    print("Running feature ablation...")
    ab = ablation(base, panels, feats, embargo)

    report = {"spec": base["meta"]["name"], "version": base["meta"]["version"],
              "embargo_start": str(embargo), "walk_forward": wf, "perturbation": pt,
              "shuffle_canary": sc, "deflated_sharpe": df, "ablation": ab}
    (REPO / "falsify" / f"REPORT{suffix}.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    _write_md(report, suffix)
    print(f"\nWrote falsify/REPORT{suffix}.json and falsify/REPORT{suffix}.md")
    return 0


def _write_md(r, suffix=""):
    wf, pt, sc, df, ab = r["walk_forward"], r["perturbation"], r["shuffle_canary"], r["deflated_sharpe"], r["ablation"]
    L = [f"# Falsification Report — {r['spec']} v{r['version']}", "",
         f"Embargoed out-of-sample window begins **{r['embargo_start'][:10]}** and is evaluated once, last.", ""]

    L += ["## Executive summary (plain English)", ""]
    L += [f"This report tries to *disprove* the strategy's edge five ways. "
          f"**Shuffle canary:** {sc['verdict'].lower()} — when we destroy the time-order of returns the "
          f"edge {'survives (bad)' if sc['edge_survived_shuffle'] else 'disappears, as a real (non-leaking) strategy should'}. "
          f"**Parameter sensitivity:** {pt['verdict'].lower()} (worst return swing {pt['max_abs_return_swing']:+.1%} when every "
          f"threshold is moved ±20%). **Deflated Sharpe** (after accounting for {df['trials']} configurations tried) is "
          f"**{df['deflated_sharpe_ratio']:.2f}** — it {df['interpretation']}. **Walk-forward** picks parameters only on past "
          f"data; the embargoed window returns {wf['embargo_oos']['return']:+.1%}. **Ablation** shows which inputs matter (below). "
          f"Backtested and forward performance do not predict future results; this project executes zero trades.", ""]

    L += ["## 1. Walk-forward (out-of-sample by construction)", "",
          "| Fold | Train ≤ | Validate < | Selected config | Val Sharpe | Val return |",
          "|--:|----|----|----|--:|--:|"]
    for f in wf.get("folds", []):
        L.append(f"| {f['fold']} | {f['train_end']} | {f['val_end']} | {f['selected']} | "
                 f"{f['val_sharpe']:.2f} | {f['val_return']:+.1%} |")
    L += ["", f"**Embargoed window (evaluated once, last)** — config `{wf['embargo_selected']}` chosen on pre-embargo data: "
          f"return {wf['embargo_oos']['return']:+.1%}, Sharpe {wf['embargo_oos']['sharpe']:.2f}, "
          f"maxDD {wf['embargo_oos']['max_dd']:.1%} over {wf['embargo_oos']['hours']} hours.", ""]

    L += ["## 2. Parameter perturbation (±20% each)", "",
          f"Baseline pre-embargo return {pt['baseline_return']:+.1%}, Sharpe {pt['baseline_sharpe']:.2f}. "
          f"**Verdict: {pt['verdict']}** (max abs return swing {pt['max_abs_return_swing']:+.1%}).", "",
          "| Param change | Return | Sharpe | Max DD | Δ return |", "|----|--:|--:|--:|--:|"]
    for row in pt["rows"]:
        L.append(f"| {row['param']} | {row['return']:+.1%} | {row['sharpe']:.2f} | "
                 f"{row['max_dd']:.1%} | {row['d_return']:+.1%} |")

    L += ["", "## 3. Shuffled-data canary", "",
          f"Fixed seed {sc['seed']}. Real: return {sc['real_return']:+.1%}, Sharpe {sc['real_sharpe']:.2f}. "
          f"Shuffled: return {sc['shuffled_return']:+.1%}, Sharpe {sc['shuffled_sharpe']:.2f}.", "",
          f"**{sc['verdict']}**", ""]
    if sc["edge_survived_shuffle"]:
        L.append("> 🔴 The edge survived shuffling — this indicates possible lookahead/leakage. Investigate before trusting results.")

    L += ["", "## 4. Deflated Sharpe ratio", "",
          f"- Observed annualized Sharpe: **{df['observed_sharpe_annual']:.2f}** ({df['n_obs']} hourly obs, "
          f"skew {df['skew']:.2f}, kurtosis {df['kurt']:.2f})",
          f"- Configurations tried (trials): **{df['trials']}**; variance of trial Sharpes: {df['var_sr_trials']:.2e}",
          f"- Deflated benchmark SR* (per period): {df['deflated_benchmark_sr_per_period']:.5f}",
          f"- **Deflated Sharpe Ratio: {df['deflated_sharpe_ratio']:.3f}** — {df['interpretation']}",
          f"- Reference: {df['reference']}", ""]

    L += ["## 5. Feature ablation (out-of-sample)", "",
          f"Full model OOS: return {ab['full_oos_return']:+.1%}, Sharpe {ab['full_oos_sharpe']:.2f}.", "",
          "| Dropped feature | OOS return | OOS Sharpe | Return degradation |", "|----|--:|--:|--:|"]
    for row in ab["rows"]:
        L.append(f"| {row['dropped_feature']} | {row['oos_return']:+.1%} | {row['oos_sharpe']:.2f} | "
                 f"{row['degradation_return']:+.1%} |")

    L += ["", "---", "*Disclaimer: backtested performance does not predict live results. This project "
          "executes zero trades. Data: Binance hourly OHLCV + CoinMarketCap Fear & Greed.*"]
    (REPO / "falsify" / f"REPORT{suffix}.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
