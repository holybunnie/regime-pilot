#!/usr/bin/env python3
"""Generate spec/universe_official_149.json — a 149-token universe file the engine can use
as a one-line drop-in for the brief's official BEP-20 list.

IMPORTANT: until the team provides the exact official 149-token list, this is a BEST-EFFORT
candidate of 149 real, liquid tickers (large/mid-cap, most with a Binance USDT spot pair and a
CoinMarketCap listing). It is structurally identical to spec/universe.json so swapping is a
one-line config change. Symbols that cannot be resolved against the live data source are flagged
(not crashed) by `make verify-universe` / engine/data/fetch.py.

Run: python cli/build_universe_149.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "spec" / "universe_official_149.json"

# Real, well-known liquid tickers (curated; not the official brief list — see header note).
SYMBOLS = [
    "BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "TRX", "DOT", "LINK",
    "AVAX", "LTC", "UNI", "ATOM", "CAKE", "MATIC", "SHIB", "BCH", "NEAR", "APT",
    "ICP", "FIL", "ARB", "OP", "ETC", "XLM", "INJ", "IMX", "HBAR", "VET",
    "SUI", "GRT", "AAVE", "RUNE", "ALGO", "FTM", "SAND", "MANA", "AXS", "EGLD",
    "THETA", "FLOW", "XTZ", "CHZ", "EOS", "KAVA", "MKR", "SNX", "LDO", "CRV",
    "COMP", "ENJ", "ZEC", "DASH", "ZIL", "BAT", "1INCH", "GALA", "APE", "GMX",
    "DYDX", "RNDR", "FET", "OCEAN", "ROSE", "CELO", "KSM", "QNT", "NEO", "IOTA",
    "WAVES", "MINA", "GMT", "LRC", "ANKR", "BAL", "YFI", "SUSHI", "UMA", "KNC",
    "STORJ", "BAND", "OGN", "SKL", "AUDIO", "MASK", "ENS", "CVX", "FXS", "RPL",
    "STX", "JASMY", "WOO", "JOE", "CFX", "AR", "ASTR", "MAGIC", "HOOK", "ID",
    "BLUR", "PEPE", "FLOKI", "BONK", "WIF", "JTO", "PYTH", "TIA", "SEI", "ORDI",
    "BEAM", "ONDO", "JUP", "STRK", "ENA", "W", "ETHFI", "OMNI", "SAGA", "TAO",
    "AKT", "NOT", "ZK", "ZRO", "IO", "BB", "LISTA", "ALT", "MANTA", "DYM",
    "PIXEL", "PORTAL", "AEVO", "METIS", "AXL", "GAS", "PENDLE", "SUPER", "C98", "TWT",
    "ARKM", "EDU", "HFT", "PERP", "RDNT", "SSV", "USTC", "RSR", "COTI",
]


def build():
    seen, tokens = set(), []
    for s in SYMBOLS:
        if s in seen:
            continue
        seen.add(s)
        tokens.append({"symbol": s, "binance_pair": f"{s}USDT", "cmc_symbol": s})
    if len(tokens) != 149:
        print(f"WARNING: have {len(tokens)} unique symbols, expected 149", file=sys.stderr)
    obj = {
        "_note": "BEST-EFFORT candidate for the brief's official 149 BEP-20 list — real liquid "
                 "tickers, structurally identical to universe.json. Replace with the exact "
                 "official list when provided (keep the same shape). Symbols that don't resolve "
                 "against the live source are flagged, not crashed (engine/data/fetch.py).",
        "_status": "CANDIDATE — replace with the official 149-token list from the brief",
        "quote": "USDT",
        "benchmark_symbol": "BTC",
        "tokens": tokens,
    }
    OUT.write_text(json.dumps(obj, indent=2) + "\n")
    print(f"wrote {OUT} with {len(tokens)} tokens")


if __name__ == "__main__":
    build()
