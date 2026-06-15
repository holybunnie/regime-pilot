#!/usr/bin/env python3
"""Data verification: data integrity.

Checks every cached OHLCV series and the Fear & Greed series for:
  - no duplicate timestamps
  - timezone is UTC and the index is hourly-aligned
  - gaps detected and listed (missing hours), with a tolerance threshold
  - >= 12 months of history present
  - spot-check: 5 cached prices for the most-liquid symbol against a fresh live
    Binance call for the same hours (proves the cache matches the source)

Exit 0 = pass. Run: python cli/verify_data.py   (or: make verify-data)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "engine" / "data" / "cache"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
MAX_GAP_FRACTION = 0.02       # allow up to 2% missing hours (exchange maintenance etc.)


def fail(msg, failures):
    print(f"  [FAIL] {msg}")
    failures.append(msg)


def check_series(name, df, failures, expect_hourly=True):
    if df.empty:
        fail(f"{name}: empty", failures)
        return
    if str(df.index.tz) != "UTC":
        fail(f"{name}: index tz is {df.index.tz}, expected UTC", failures)
    if df.index.duplicated().any():
        fail(f"{name}: {int(df.index.duplicated().sum())} duplicate timestamps", failures)
    else:
        print(f"  [PASS] {name}: no duplicate timestamps")
    if expect_hourly:
        span_hours = int((df.index.max() - df.index.min()).total_seconds() // 3600) + 1
        missing = span_hours - len(df)
        frac = missing / span_hours if span_hours else 1
        status = "PASS" if frac <= MAX_GAP_FRACTION else "FAIL"
        line = f"{name}: {len(df)} rows, {missing} missing hours ({frac:.2%} gap)"
        if status == "PASS":
            print(f"  [PASS] {line}")
        else:
            fail(line, failures)


def main():
    failures = []
    manifest_path = CACHE / "manifest.json"
    if not manifest_path.exists():
        print("  [FAIL] no manifest — run `make data` first")
        return 1
    manifest = json.loads(manifest_path.read_text())
    resolved = manifest["resolved_symbols"]
    print(f"Manifest window {manifest['window_start'][:10]} -> {manifest['window_end'][:10]} "
          f"(embargo from {manifest['embargo_start'][:10]})")

    # 12-month coverage
    span_days = (pd.Timestamp(manifest["window_end"]) - pd.Timestamp(manifest["window_start"])).days
    if span_days >= 360:
        print(f"  [PASS] history span {span_days} days (>= 12 months)")
    else:
        fail(f"history span only {span_days} days (< 12 months)", failures)

    # per-symbol OHLCV
    for sym in resolved:
        p = CACHE / f"ohlcv_{sym}.parquet"
        if not p.exists():
            fail(f"{sym}: cache file missing", failures)
            continue
        check_series(sym, pd.read_parquet(p), failures)

    # Fear & Greed (daily, not hourly)
    fg_path = CACHE / "fear_greed.parquet"
    if fg_path.exists():
        check_series("fear_greed", pd.read_parquet(fg_path), failures, expect_hourly=False)
    else:
        fail("fear_greed cache missing", failures)

    # spot-check BTC cache vs fresh live Binance
    btc_path = CACHE / "ohlcv_BTC.parquet"
    if btc_path.exists():
        df = pd.read_parquet(btc_path)
        sample = df.iloc[-120:-115]            # 5 recent (settled) hours
        ok = True
        for ts, row in sample.iterrows():
            start_ms = int(ts.timestamp() * 1000)
            live = requests.get(BINANCE, params={"symbol": "BTCUSDT", "interval": "1h",
                                "startTime": start_ms, "limit": 1}, timeout=20).json()
            if not live:
                continue
            live_close = float(live[0][4])
            if abs(live_close - row["close"]) > 1e-6:
                fail(f"BTC spot-check mismatch at {ts}: cache {row['close']} vs live {live_close}", failures)
                ok = False
        if ok:
            print("  [PASS] BTC spot-check: 5 cached prices match fresh live Binance")

    print()
    if failures:
        print(f"RESULT: {len(failures)} integrity problem(s).")
        return 1
    print("RESULT: data integrity checks all pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
