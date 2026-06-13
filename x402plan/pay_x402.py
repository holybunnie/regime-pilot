#!/usr/bin/env python3
"""Execute a REAL x402 paid request to the CoinMarketCap x402 MCP endpoint.

Flow (x402 "exact" scheme, EIP-3009 transferWithAuthorization on Base):
  1. Call the tool -> HTTP 402 with a base64 PAYMENT-REQUIRED header (accepts[]).
  2. Pick the Base/USDC/eip3009 option; build a transferWithAuthorization authorization.
  3. Sign it EIP-712 (USDC domain) with the wallet key (gasless for us — the facilitator
     submits on-chain and pays gas; we only spend the $0.01 USDC).
  4. Resend with PAYMENT-SIGNATURE = base64(x402 payment payload). Server settles + returns data.

Safety: USDC moves ONLY on successful delivery, so failed attempts cost nothing. This spends
exactly $0.01 USDC. Records evidence to evidence/ and the price to x402plan/prices.json.

Run: python x402plan/pay_x402.py
"""
import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from eth_account import Account                       # noqa: E402
from attest import chain                              # noqa: E402

URL = "https://mcp.coinmarketcap.com/x402/mcp"
TOOL = "get_crypto_quotes_latest"
ARGS = {"id": "1"}   # CMC id 1 = BTC
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def rpc_post(payload, extra_headers=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


def parse_body(raw):
    raw = raw.strip()
    if "data:" in raw:
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
    return json.loads(raw) if raw else None


def usdc_balance(w3, addr):
    data = "0x70a08231" + addr[2:].lower().rjust(64, "0")
    bal = w3.eth.call({"to": w3.to_checksum_address(USDC_BASE), "data": data})
    return int(bal.hex(), 16) / 1e6


def main():
    env = chain.load_env()
    pk = (env.get("X402_BASE_PRIVATE_KEY") or env.get("ATTEST_PRIVATE_KEY") or "").strip()
    if not pk:
        print("FATAL: no X402_BASE_PRIVATE_KEY in .env")
        return 1
    acct = Account.from_key(pk)

    call = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": TOOL, "arguments": ARGS}}

    # 1) trigger 402
    code, hdrs, _ = rpc_post(call)
    if code != 402:
        print(f"expected 402, got {code}")
        return 1
    pr_header = next((v for k, v in hdrs.items() if k.upper() == "PAYMENT-REQUIRED"), None)
    reqs = json.loads(base64.b64decode(pr_header).decode())
    (REPO / "evidence" / "x402_402_challenge.json").write_text(json.dumps(reqs, indent=2))

    # 2) pick Base/USDC/eip3009 option
    opt = next(o for o in reqs["accepts"]
               if o["network"] == "eip155:8453" and o["asset"].lower() == USDC_BASE.lower()
               and o.get("extra", {}).get("assetTransferMethod") == "eip3009")
    amount = int(opt["amount"])
    print(f"402 received. Pay {amount/1e6:.2f} USDC on Base -> {opt['payTo']} (config {opt['extra'].get('x402PaymentConfigId')})")

    # balance before
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider("https://base.publicnode.com", request_kwargs={"timeout": 30}))
    bal_before = usdc_balance(w3, acct.address)
    print(f"USDC before: {bal_before:.4f}")

    # 3) build + sign EIP-3009 authorization
    now = int(time.time())
    valid_after = 0
    valid_before = now + max(60, int(opt.get("maxTimeoutSeconds", 30)))
    nonce = "0x" + os.urandom(32).hex()
    authorization = {
        "from": acct.address, "to": w3.to_checksum_address(opt["payTo"]),
        "value": str(amount), "validAfter": str(valid_after),
        "validBefore": str(valid_before), "nonce": nonce,
    }
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"}],
        },
        "domain": {"name": opt["extra"]["name"], "version": opt["extra"]["version"],
                   "chainId": 8453, "verifyingContract": w3.to_checksum_address(opt["asset"])},
        "primaryType": "TransferWithAuthorization",
        "message": {"from": acct.address, "to": w3.to_checksum_address(opt["payTo"]),
                    "value": amount, "validAfter": valid_after, "validBefore": valid_before,
                    "nonce": bytes.fromhex(nonce[2:])},
    }
    signed = Account.sign_typed_data(pk, full_message=typed)
    signature = "0x" + signed.signature.hex().lstrip("0x")

    # 4) build PAYMENT-SIGNATURE header and retry
    payment = {"x402Version": reqs.get("x402Version", 2),
               "accepted": opt,                       # echo the chosen requirement (required in v2)
               "resource": reqs.get("resource"),      # echo the resource descriptor (required in v2)
               "scheme": "exact", "network": "eip155:8453",
               "payload": {"signature": signature, "authorization": authorization}}
    header_val = base64.b64encode(json.dumps(payment).encode()).decode()
    code2, hdrs2, body2 = rpc_post(call, {"PAYMENT-SIGNATURE": header_val})
    print(f"retry with payment -> HTTP {code2}")

    result = parse_body(body2)
    settle = next((v for k, v in hdrs2.items() if "payment" in k.lower() and "response" in k.lower()), None)
    ok = code2 == 200 and result and "result" in result
    evidence = {"tool": TOOL, "args": ARGS, "amount_usdc": amount / 1e6, "pay_to": opt["payTo"],
                "config_id": opt["extra"].get("x402PaymentConfigId"),
                "http": code2, "settlement_header": settle,
                "data_excerpt": json.dumps(result)[:600] if result else None}
    (REPO / "evidence" / "x402_executed_payment.json").write_text(json.dumps(evidence, indent=2))

    if ok:
        # balance after (settlement may take a moment)
        time.sleep(6)
        bal_after = usdc_balance(w3, acct.address)
        print(f"USDC after: {bal_after:.4f}  (delta {bal_after - bal_before:+.4f})")
        print("PAID REQUEST SUCCEEDED — data returned and recorded to evidence/x402_executed_payment.json")
        if settle:
            print("settlement:", settle[:120])
        return 0
    print(f"payment not accepted (HTTP {code2}): {body2[:300]}")
    print("No USDC moves on failure. Evidence saved.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
