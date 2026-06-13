#!/usr/bin/env python3
"""Shared BSC mainnet helpers for the attestation layer.

Safety:
  - The private key is read from env only and NEVER printed/logged/returned.
  - PoA middleware is injected (BSC is proof-of-authority).
  - Gas price is floored at 0.1 Gwei and bumped 10% for reliable inclusion.
"""
import json
import os
from pathlib import Path

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

REPO = Path(__file__).resolve().parent.parent
CHAIN_ID = 56
RPCS = [
    "https://bsc-dataseed.bnbchain.org",
    "https://bsc.publicnode.com",
    "https://bsc-dataseed1.binance.org",
]


def load_env():
    env = dict(os.environ)
    f = REPO / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def get_account():
    """Return an eth_account from ATTEST_PRIVATE_KEY (or X402_BASE_PRIVATE_KEY).
    The key value is never exposed beyond this Account object."""
    env = load_env()
    pk = (env.get("ATTEST_PRIVATE_KEY") or env.get("X402_BASE_PRIVATE_KEY") or "").strip()
    if not pk:
        raise RuntimeError("no ATTEST_PRIVATE_KEY / X402_BASE_PRIVATE_KEY in .env")
    return Account.from_key(pk)


def get_w3():
    last = None
    for rpc in RPCS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if w3.eth.chain_id == CHAIN_ID:
                return w3
        except Exception as e:
            last = e
    raise RuntimeError(f"no BSC mainnet RPC reachable: {last}")


def gas_price(w3):
    floor = w3.to_wei("0.1", "gwei")
    return int(max(w3.eth.gas_price, floor) * 1.1)


def send_tx(w3, account, tx):
    """Fill nonce/chainId/gasPrice/gas, sign, send, wait. Returns the receipt."""
    tx.setdefault("chainId", CHAIN_ID)
    tx.setdefault("nonce", w3.eth.get_transaction_count(account.address))
    tx.setdefault("gasPrice", gas_price(w3))
    if "gas" not in tx:
        tx["gas"] = int(w3.eth.estimate_gas({**tx, "from": account.address}) * 1.25)
    signed = account.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(h, timeout=180)


def artifact():
    return json.loads((REPO / "attest" / "build" / "SignalAttestor.json").read_text())


def deployment():
    p = REPO / "attest" / "deployment.json"
    return json.loads(p.read_text()) if p.exists() else None
