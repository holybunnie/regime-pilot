#!/usr/bin/env python3
"""Inactive CMC Pro OHLCV adapter for the versioned post-reveal cutover.

This writes to `engine/data/cache_cmc/`; it never touches the active Binance-backed cache used by
the frozen v2 hourly committer. Activate it only with an explicit, documented source/version
cutover.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / "engine" / "data" / "cache_cmc"
UNIVERSE = REPO / "spec" / "universe.json"
CMC_IDS = REPO / "spec" / "cmc_ids.json"
ENV = REPO / ".env"

CMC_OHLCV = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/historical"
CMC_FG = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"
HISTORY_DAYS = 364
EMBARGO_DAYS = 30
CHUNK_DAYS = 90


def now_utc():
    return datetime.now(timezone.utc)


def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    env.update({k: v for k, v in os.environ.items()
                if k.startswith("CMC_") or k == "REGIME_PILOT_PRICE_SOURCE"})
    return env


def api_key(env):
    return (env.get("CMC_API_KEY") or env.get("CMC_PRO_API_KEY") or "").strip()


def _payload_asset(data, cmc_id):
    """Accept current single-asset and id-keyed v2 response shapes."""
    if isinstance(data, list):
        matches = [item for item in data if int(item.get("id", -1)) == int(cmc_id)]
        return matches[0] if matches else None
    if isinstance(data, dict) and "quotes" in data:
        return data
    if isinstance(data, dict):
        return data.get(str(cmc_id)) or data.get(int(cmc_id))
    return None


def normalize_ohlcv(payload, cmc_id):
    """Normalize one CMC response to the engine cache contract.

    CMC's `quote.USD.volume` is retained as `volume_24h_usd`; the engine must not multiply it by
    price or roll it again as it does for Binance base-asset candle volume.
    """
    status = payload.get("status", {})
    if status and int(status.get("error_code", 0)) != 0:
        raise RuntimeError(f"CMC OHLCV error {status.get('error_code')}: {status.get('error_message')}")
    asset = _payload_asset(payload.get("data"), cmc_id)
    if not asset:
        return pd.DataFrame()
    rows = []
    for item in asset.get("quotes", []):
        quote = item.get("quote", {}).get("USD", {})
        ts = item.get("time_open") or quote.get("timestamp") or item.get("timestamp")
        if not ts or not quote:
            continue
        rows.append({
            "ts": pd.Timestamp(ts),
            "open": float(quote["open"]),
            "high": float(quote["high"]),
            "low": float(quote["low"]),
            "close": float(quote["close"]),
            "volume_24h_usd": float(quote.get("volume", 0.0)),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.floor("h")
    df = df.set_index("ts").sort_index()
    return df[~df.index.duplicated(keep="last")]


def fetch_chunk(key, cmc_id, start, end, session=requests):
    params = {
        "id": str(cmc_id),
        "time_start": int(start.timestamp()),
        "time_end": int(end.timestamp()),
        "time_period": "hourly",
        "interval": "hourly",
        "convert": "USD",
        "skip_invalid": "false",
    }
    last_error = None
    for attempt in range(5):
        try:
            response = session.get(
                CMC_OHLCV,
                headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"},
                params=params,
                timeout=30,
            )
            payload = response.json()
            if response.status_code == 200:
                return normalize_ohlcv(payload, cmc_id)
            last_error = payload.get("status", payload)
            if response.status_code != 429:
                break
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"CMC OHLCV request failed for id={cmc_id}: {last_error}")


def fetch_ohlcv(key, cmc_id, start, end):
    frames = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        frame = fetch_chunk(key, cmc_id, cursor, chunk_end)
        if not frame.empty:
            frames.append(frame)
        cursor = chunk_end
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames).sort_index()
    return combined[~combined.index.duplicated(keep="last")]


def fetch_fear_greed(key):
    response = requests.get(
        CMC_FG,
        headers={"X-CMC_PRO_API_KEY": key},
        params={"limit": 500},
        timeout=30,
    )
    payload = response.json()
    if response.status_code != 200 or int(payload.get("status", {}).get("error_code", 0)) != 0:
        raise RuntimeError(f"CMC Fear & Greed failed: {payload.get('status', payload)}")
    df = pd.DataFrame(payload["data"])
    df["ts"] = pd.to_datetime(df["timestamp"].astype(int), unit="s", utc=True)
    df["fear_greed"] = df["value"].astype(float)
    return df[["ts", "fear_greed"]].set_index("ts").sort_index()


def main():
    env = load_env()
    key = api_key(env)
    if not key:
        print("FATAL: CMC_API_KEY is required for the CMC Pro data path")
        return 1
    universe = json.loads(UNIVERSE.read_text())
    ids = json.loads(CMC_IDS.read_text())
    end = now_utc().replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=HISTORY_DAYS)
    embargo_start = end - timedelta(days=EMBARGO_DAYS)
    CACHE.mkdir(parents=True, exist_ok=True)

    resolved = []
    for token in universe["tokens"]:
        symbol = token["symbol"]
        if symbol not in ids:
            raise RuntimeError(f"no stable CMC id configured for {symbol}")
        path = CACHE / f"ohlcv_{symbol}.parquet"
        frame = fetch_ohlcv(key, ids[symbol], start, end)
        if frame.empty:
            raise RuntimeError(f"CMC returned no OHLCV for {symbol}")
        frame.to_parquet(path)
        resolved.append(symbol)
        print(f"  [OK] {symbol:<5} {len(frame):>6} hrs")

    fetch_fear_greed(key).to_parquet(CACHE / "fear_greed.parquet")
    manifest = {
        "generated_at": now_utc().isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "embargo_start": embargo_start.isoformat(),
        "embargo_days": EMBARGO_DAYS,
        "resolved_symbols": resolved,
        "excluded": [],
        "sources": {
            "ohlcv": "coinmarketcap /v2/cryptocurrency/ohlcv/historical hourly USD",
            "volume": "CMC quote.USD.volume retained as volume_24h_usd",
            "fear_greed": "coinmarketcap /v3/fear-and-greed/historical",
        },
        "cmc_ids": {symbol: ids[symbol] for symbol in resolved},
    }
    (CACHE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"CMC cache ready at {CACHE}; not active until explicit versioned cutover.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
