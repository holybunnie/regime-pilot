import json

import pandas as pd

from engine import backtest
from engine import datasource
from engine.data import cmc_pro


SAMPLE = {
    "status": {"error_code": 0},
    "data": {
        "id": 1,
        "symbol": "BTC",
        "quotes": [
            {
                "time_open": "2026-06-18T12:00:00.000Z",
                "quote": {
                    "USD": {
                        "open": 100.0,
                        "high": 110.0,
                        "low": 95.0,
                        "close": 105.0,
                        "volume": 123456789.0,
                        "timestamp": "2026-06-18T12:59:59.000Z"
                    }
                }
            }
        ]
    }
}


def test_cmc_normalization_preserves_quote_volume():
    frame = cmc_pro.normalize_ohlcv(SAMPLE, 1)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume_24h_usd"]
    assert frame.iloc[0]["close"] == 105.0
    assert frame.iloc[0]["volume_24h_usd"] == 123456789.0
    assert str(frame.index.tz) == "UTC"


def test_cmc_source_requires_explicit_cutover():
    assert datasource.select_price_source({"CMC_API_KEY": "pro-capable"}) == "binance"
    assert datasource.cmc_pro_available({"CMC_API_KEY": "pro-capable"})
    assert datasource.select_price_source({
        "CMC_API_KEY": "pro-capable",
        "REGIME_PILOT_PRICE_SOURCE": "cmc_pro",
    }) == "cmc_pro"


def test_current_universe_has_stable_cmc_ids():
    ids = json.loads(cmc_pro.CMC_IDS.read_text())
    universe = json.loads(cmc_pro.UNIVERSE.read_text())
    symbols = {token["symbol"] for token in universe["tokens"]}
    assert symbols == set(ids)


def test_engine_uses_cmc_quote_volume_without_reconversion(tmp_path, monkeypatch):
    idx = pd.date_range("2026-06-18", periods=3, freq="h", tz="UTC")
    for symbol, offset in (("BTC", 0), ("ETH", 10)):
        pd.DataFrame({
            "open": [100 + offset] * 3,
            "high": [101 + offset] * 3,
            "low": [99 + offset] * 3,
            "close": [100 + offset] * 3,
            "volume_24h_usd": [1000 + offset, 2000 + offset, 3000 + offset],
        }, index=idx).to_parquet(tmp_path / f"ohlcv_{symbol}.parquet")
    pd.DataFrame({"fear_greed": [50]}, index=[idx[0]]).to_parquet(
        tmp_path / "fear_greed.parquet")
    monkeypatch.setattr(backtest, "CACHE", tmp_path)
    panels = backtest.load_panels(["ETH"])
    assert list(panels["close"].columns) == ["ETH"]
    assert panels["btc"].iloc[0] == 100
    assert panels["dvol24"]["ETH"].tolist() == [1010, 2010, 3010]
