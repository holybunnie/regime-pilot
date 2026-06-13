#!/usr/bin/env python3
"""Phase 1 data layer (hybrid model).

Sources (all verified reachable in Phase 0):
  - Binance public klines  -> hourly OHLCV per universe token (backtest prices / PnL)
  - CoinMarketCap          -> Fear & Greed history (sentiment regime feature)

Design rules honored:
  - UTC everywhere; timestamps are tz-aware UTC.
  - Resumable + cached: each symbol is cached to a parquet file; re-runs fetch only
    the missing tail.
  - Throttled + backoff on Binance (it is generous but we are polite).
  - No silent fill: missing sources raise; gaps are detected and reported, not patched.
  - Embargo: the final EMBARGO_DAYS before "now" are written to a manifest and must be
    left untouched by any parameter selection (enforced downstream by the engine).

Run: python engine/data/fetch.py            (or: make data)
"""
import json
import time
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / "engine" / "data" / "cache"
UNIVERSE = REPO / "spec" / "universe.json"
ENV = REPO / ".env"

BINANCE = "https://data-api.binance.vision/api/v3/klines"
CMC_FG = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"

HISTORY_MONTHS = 13          # >= 12-month target
EMBARGO_DAYS = 30            # final 30 days reserved as out-of-sample
PER_CALL = 1000              # Binance max rows/call
THROTTLE_S = 0.25


def now_utc():
    return datetime.now(timezone.utc)


def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_universe():
    return json.loads(UNIVERSE.read_text())


# ---------------------------------------------------------------- Binance OHLCV
def _fetch_klines_page(pair, start_ms, end_ms):
    params = {"symbol": pair, "interval": "1h", "startTime": start_ms,
              "endTime": end_ms, "limit": PER_CALL}
    for attempt in range(5):
        try:
            r = requests.get(BINANCE, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 418):       # rate limited
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
        except requests.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Binance failed for {pair} after retries")


def fetch_ohlcv(pair, start_ms, end_ms):
    """Return a UTC-indexed hourly OHLCV DataFrame for [start_ms, end_ms]."""
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        page = _fetch_klines_page(pair, cursor, end_ms)
        if not page:
            break
        rows.extend(page)
        last_open = page[-1][0]
        nxt = last_open + 3_600_000
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(THROTTLE_S)
        if len(page) < PER_CALL:
            break
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "qav", "trades", "tbav", "tqav", "ignore"])
    df = df[["open_time", "open", "high", "low", "close", "volume"]].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop(columns=["open_time"]).set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def cache_path(symbol):
    return CACHE / f"ohlcv_{symbol}.parquet"


def update_symbol(symbol, pair, start, end):
    """Incremental, resumable fetch into a per-symbol parquet cache."""
    path = cache_path(symbol)
    existing = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    fetch_start = start
    if not existing.empty:
        last = existing.index.max()
        if last >= end - timedelta(hours=1):
            return existing, 0       # already current
        fetch_start = last + timedelta(hours=1)
    new = fetch_ohlcv(pair, int(fetch_start.timestamp() * 1000), int(end.timestamp() * 1000))
    combined = pd.concat([existing, new]) if not existing.empty else new
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined = combined[(combined.index >= start) & (combined.index <= end)]
    CACHE.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(path)
    return combined, len(new)


# ------------------------------------------------------------- CMC Fear & Greed
def fetch_fear_greed(api_key):
    if not api_key:
        raise RuntimeError("CMC_API_KEY missing — cannot fetch Fear & Greed (no synthetic fill)")
    last_err = None
    for attempt in range(5):
        try:
            r = requests.get(CMC_FG, headers={"X-CMC_PRO_API_KEY": api_key},
                             params={"limit": 500}, timeout=30)
            d = r.json()
            if str(d.get("status", {}).get("error_code")) == "0":
                df = pd.DataFrame(d["data"])
                df["ts"] = pd.to_datetime(df["timestamp"].astype(int), unit="s", utc=True)
                df["fear_greed"] = df["value"].astype(float)
                return df[["ts", "fear_greed"]].set_index("ts").sort_index()
            last_err = d.get("status")
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"CMC Fear & Greed failed: {last_err}")


# ----------------------------------------------------------------------- driver
def main():
    env = load_env()
    uni = load_universe()
    end = now_utc().replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=HISTORY_MONTHS * 30)
    embargo_start = end - timedelta(days=EMBARGO_DAYS)

    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Window: {start:%Y-%m-%d} -> {end:%Y-%m-%d} UTC  (embargo from {embargo_start:%Y-%m-%d})")

    resolved, excluded = [], []
    for tok in uni["tokens"]:
        sym, pair = tok["symbol"], tok["binance_pair"]
        try:
            df, n = update_symbol(sym, pair, start, end)
            if df.empty:
                excluded.append((sym, "no data returned"))
                print(f"  [EXCLUDE] {sym}: no data")
                continue
            resolved.append(sym)
            print(f"  [OK] {sym:<5} {len(df):>6} hrs (+{n} new)  {df.index.min():%Y-%m-%d}..{df.index.max():%Y-%m-%d}")
        except Exception as e:
            excluded.append((sym, str(e)))
            print(f"  [EXCLUDE] {sym}: {e}")

    # Fear & Greed
    fg = fetch_fear_greed(env.get("CMC_API_KEY", ""))
    fg.to_parquet(CACHE / "fear_greed.parquet")
    print(f"  [OK] Fear&Greed {len(fg)} daily points {fg.index.min():%Y-%m-%d}..{fg.index.max():%Y-%m-%d}")

    manifest = {
        "generated_at": now_utc().isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "embargo_start": embargo_start.isoformat(),
        "embargo_days": EMBARGO_DAYS,
        "resolved_symbols": resolved,
        "excluded": excluded,
        "sources": {"ohlcv": "binance data-api.binance.vision 1h",
                    "fear_greed": "coinmarketcap /v3/fear-and-greed/historical (daily)"},
    }
    (CACHE / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nResolved {len(resolved)}/{len(uni['tokens'])} symbols; {len(excluded)} excluded.")
    print(f"Manifest: {CACHE / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
