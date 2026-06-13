#!/usr/bin/env python3
"""Deploy SignalAttestor to BSC mainnet. Idempotent and balance-checked.

Safety:
  - If a deployment.json already points at a contract that HAS code on-chain, this
    refuses to redeploy (prevents wasting gas / fragmenting the attestation record).
  - Estimates gas and checks the wallet balance covers it before sending.
  - Never prints the private key.

Run: python attest/deploy.py        (or: make attest-deploy)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from attest import chain   # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def main():
    w3 = chain.get_w3()
    acct = chain.get_account()
    art = chain.artifact()

    # idempotency: already deployed with live code?
    existing = chain.deployment()
    if existing and w3.eth.get_code(w3.to_checksum_address(existing["address"])) not in (b"", b"0x"):
        print(f"Already deployed at {existing['address']} (has on-chain code). Not redeploying.")
        print(f"BscScan: https://bscscan.com/address/{existing['address']}")
        return 0

    C = w3.eth.contract(abi=art["abi"], bytecode=art["bin"])
    deploy_tx = C.constructor().build_transaction({"from": acct.address, "nonce":
                                                   w3.eth.get_transaction_count(acct.address)})
    gas = int(w3.eth.estimate_gas({"from": acct.address, "data": deploy_tx["data"]}) * 1.25)
    gp = chain.gas_price(w3)
    cost_bnb = gas * gp / 1e18
    bal = w3.eth.get_balance(acct.address) / 1e18
    print(f"Deployer     : {acct.address}")
    print(f"Balance      : {bal:.6f} BNB")
    print(f"Est. gas     : {gas} @ {gp/1e9:.3f} Gwei = {cost_bnb:.6f} BNB")
    if bal < cost_bnb * 1.5:
        print(f"INSUFFICIENT BALANCE: need ~{cost_bnb*1.5:.6f} BNB buffer, have {bal:.6f}. Aborting.")
        return 1

    rcpt = chain.send_tx(w3, acct, {"data": deploy_tx["data"], "gas": gas})
    addr = rcpt["contractAddress"]
    info = {
        "address": addr,
        "deploy_tx": rcpt["transactionHash"].hex(),
        "block": rcpt["blockNumber"],
        "chain_id": chain.CHAIN_ID,
        "deployer": acct.address,
        "gas_used": rcpt["gasUsed"],
        "abi": art["abi"],
    }
    (REPO / "attest" / "deployment.json").write_text(json.dumps(info, indent=2))
    print(f"\nDEPLOYED ✅  {addr}")
    print(f"Deploy tx   : 0x{rcpt['transactionHash'].hex().lstrip('0x')}")
    print(f"Gas used    : {rcpt['gasUsed']}")
    print(f"BscScan     : https://bscscan.com/address/{addr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
