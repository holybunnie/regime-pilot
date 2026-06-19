#!/usr/bin/env python3
"""Live capability probe for the CMC Pro hourly historical-data path."""
import sys
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from engine.data import cmc_pro  # noqa: E402


def main():
    key = cmc_pro.api_key(cmc_pro.load_env())
    if not key:
        print("[FAIL] CMC_API_KEY missing")
        return 1
    end = cmc_pro.now_utc().replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    start = end - timedelta(hours=6)
    try:
        frame = cmc_pro.fetch_chunk(key, 1, start, end)
    except Exception as exc:
        print(f"[FAIL] CMC Pro hourly OHLCV unavailable: {exc}")
        return 1
    checks = [(not frame.empty, "BTC hourly history returned rows")]
    if not frame.empty:
        checks.extend([
            (str(frame.index.tz) == "UTC", "timestamps normalized to UTC"),
            ("volume_24h_usd" in frame, "CMC quote volume preserved without Binance conversion"),
            (frame.index.is_unique, "timestamps are unique"),
        ])
    for ok, message in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {message}")
    if not all(ok for ok, _ in checks):
        return 1
    print(f"RESULT: CMC Pro hourly OHLCV capability confirmed ({len(frame)} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
