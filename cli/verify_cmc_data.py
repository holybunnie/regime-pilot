#!/usr/bin/env python3
"""Verify the separate CMC Pro shadow cache and run the live v2 spec against it."""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine import backtest as bt  # noqa: E402
from engine.data import cmc_pro    # noqa: E402

CACHE = cmc_pro.CACHE
MIN_HISTORY_DAYS = 360


def main():
    failures = []

    def check(condition, message):
        print(f"  [{'PASS' if condition else 'FAIL'}] {message}")
        if not condition:
            failures.append(message)

    manifest_path = CACHE / "manifest.json"
    check(manifest_path.exists(), "CMC shadow manifest exists")
    if not manifest_path.exists():
        print("RESULT: run `make data-cmc` first.")
        return 1

    manifest = json.loads(manifest_path.read_text())
    symbols = manifest.get("resolved_symbols", [])
    configured = json.loads(cmc_pro.CMC_IDS.read_text())
    check(set(symbols) == set(configured), "shadow cache covers every configured CMC asset")

    span_days = (
        pd.Timestamp(manifest["window_end"]) - pd.Timestamp(manifest["window_start"])
    ).days
    check(span_days >= MIN_HISTORY_DAYS, f"history span is {span_days} days (>= {MIN_HISTORY_DAYS})")

    for symbol in symbols:
        path = CACHE / f"ohlcv_{symbol}.parquet"
        check(path.exists(), f"{symbol}: cache file exists")
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        check(not frame.empty, f"{symbol}: cache is non-empty")
        check(str(frame.index.tz) == "UTC", f"{symbol}: timestamps are UTC")
        check(frame.index.is_unique, f"{symbol}: timestamps are unique")
        check("volume_24h_usd" in frame, f"{symbol}: CMC USD quote-volume is preserved")
        expected = int((frame.index.max() - frame.index.min()).total_seconds() // 3600) + 1
        check(expected - len(frame) <= 2, f"{symbol}: hourly coverage has at most 2 gaps")

    if not failures:
        original_cache = bt.CACHE
        try:
            bt.CACHE = CACHE
            spec = json.loads((REPO / "spec" / "regime_pilot_v2.spec.json").read_text())
            result = bt.run(spec)
            check(not result["equity"].empty, "v2 completes against the CMC shadow cache")
            print(f"         window {result['summary']['window_start'][:10]}.."
                  f"{result['summary']['window_end'][:10]}, "
                  f"{result['summary']['trade_count']} trades")
        finally:
            bt.CACHE = original_cache

    print()
    if failures:
        print(f"RESULT: {len(failures)} CMC shadow-data problem(s).")
        return 1
    print("RESULT: CMC shadow cache and v2 shadow backtest pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
