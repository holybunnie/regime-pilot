#!/usr/bin/env python3
"""Environment live verification: external dependencies + credentials.

Prints a plain-English table of REACHABLE/UNREACHABLE and PRESENT/MISSING.
Exit 0 if every REQUIRED dependency is reachable and the CMC key is present+valid.
Optional items (wallet, x402) print status but never fail the gate.

Run: python cli/verify_environment.py   (or: make verify-environment)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    f = REPO / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k in (
        "CMC_API_KEY", "X402_BASE_PRIVATE_KEY", "ATTEST_PRIVATE_KEY")})
    return env


def http_code(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "regime-pilot/verify"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def rpc_chain_id(urls, timeout=12):
    """Try each RPC URL until one answers eth_chainId. Returns (chain_id, url_used)."""
    if isinstance(urls, str):
        urls = [urls]
    data = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    for url in urls:
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json", "User-Agent": "regime-pilot/verify"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                cid = json.load(r).get("result")
                if cid:
                    return cid, url
        except Exception:
            continue
    return None, None


def main():
    env = load_env()
    rows = []          # (label, status_ok, detail)
    required_ok = True

    # --- network deps ---
    cmc = http_code("https://pro-api.coinmarketcap.com/v1/key/info")
    rows.append(("CMC REST API", cmc in (200, 401), f"HTTP {cmc}"))

    mcp = http_code("https://mcp.coinmarketcap.com/mcp")
    rows.append(("CMC MCP (/mcp, POST-only)", mcp in (405, 400, 200), f"HTTP {mcp} (405=exists)"))

    bsc, bsc_url = rpc_chain_id([
        "https://bsc-dataseed.bnbchain.org",
        "https://bsc.publicnode.com",
        "https://bsc-dataseed1.binance.org"])
    rows.append(("BSC mainnet RPC", bsc == "0x38", f"chainId {bsc} via {bsc_url or '-'}"))

    klines = http_code("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1")
    rows.append(("Binance hourly OHLCV (backtest data)", klines == 200, f"HTTP {klines}"))

    gh = http_code("https://github.com")
    rows.append(("GitHub", gh == 200, f"HTTP {gh}"))

    for _, ok, _ in rows:
        required_ok = required_ok and ok

    # BSC testnet — informational only (used for deploy rehearsal, not the deliverable)
    tbsc, tbsc_url = rpc_chain_id([
        "https://bsc-testnet.publicnode.com",
        "https://data-seed-prebsc-1-s1.bnbchain.org:8545",
        "https://bsc-testnet-dataseed.bnbchain.org"])

    # --- credentials (CMC required; wallet optional) ---
    cmc_key = env.get("CMC_API_KEY", "")
    key_valid = False
    detail = "MISSING"
    if cmc_key:
        try:
            req = urllib.request.Request(
                "https://pro-api.coinmarketcap.com/v1/key/info",
                headers={"X-CMC_PRO_API_KEY": cmc_key})
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.load(r)
            key_valid = d.get("status", {}).get("error_code") == 0
            left = d.get("data", {}).get("usage", {}).get("current_month", {}).get("credits_left")
            detail = f"PRESENT, valid, {left} credits left" if key_valid else "PRESENT but rejected"
        except Exception as e:
            detail = f"PRESENT but check failed: {e}"
    rows.append(("CMC_API_KEY (required)", key_valid, detail))
    required_ok = required_ok and key_valid

    # wallet (optional — does not fail the gate)
    wallet_key = env.get("ATTEST_PRIVATE_KEY") or env.get("X402_BASE_PRIVATE_KEY")
    wstatus = "PRESENT" if wallet_key else "MISSING (needed for attestation/x402)"

    # --- print table ---
    print("=" * 64)
    print(" ENVIRONMENT VERIFICATION")
    print("=" * 64)
    for label, ok, det in rows:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label:<42} {det}")
    tinfo = f"chainId {tbsc} via {tbsc_url}" if tbsc == "0x61" else "unreachable now (non-blocking)"
    print(f"  [INFO] BSC testnet RPC                       {tinfo}")
    print(f"  [INFO] attestation/x402 wallet              {wstatus}")
    print("=" * 64)
    if required_ok:
        print("RESULT: all required dependencies reachable and CMC key valid.")
        return 0
    print("RESULT: one or more REQUIRED checks failed (see FAIL rows above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
