#!/usr/bin/env python3
"""Independently verify every on-chain commit and write attest/VERIFICATION.md.

For each commit in attest/commits_public.csv:
  - reconstruct the payload (deterministic from the frozen spec + public market data)
  - obtain the salt: from attest/reveals.json if present (the INDEPENDENT path judges
    use after reveal), else recompute via ATTEST_SALT_SEED (the owner path)
  - recompute hash = keccak(canonical_json(payload) || salt)
  - read the on-chain commit and assert hash matches
  - check promptness: the block timestamp falls within the signal's effective hour
    (commit happened before that hour's outcome could be known)

Also reconstructs the forward-test equity curve from the committed target weights.

Run: python attest/verify.py   (or: make attest-verify)
"""
import csv
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from attest import chain                                          # noqa: E402
from attest.hashing import commit_hash, deterministic_salt        # noqa: E402
from attest.live_signal import compute_signal                     # noqa: E402
from engine import backtest as bt                                 # noqa: E402

# Candidate frozen specs, tried in order. Each commit is matched to whichever spec
# reproduces its on-chain hash — so a v1->v2 switch leaves all past commits verifiable.
SPECS = [REPO / "spec" / "regime_pilot.spec.json",
         REPO / "spec" / "regime_pilot_v2.spec.json"]
PUBLIC = REPO / "attest" / "commits_public.csv"
REVEALS = REPO / "attest" / "reveals.json"
OUT = REPO / "attest" / "VERIFICATION.md"


def forward_equity(rows):
    """Equity from committed weights: hold each signal's weights until the next commit."""
    universe = [t["symbol"] for t in
                json.loads((REPO / "spec" / "universe.json").read_text())["tokens"]]
    panels = bt.load_panels(universe)
    rets = panels["close"].pct_change()
    eq = 1.0
    curve = []
    for i in range(len(rows) - 1):
        t0 = pd.Timestamp(rows[i]["payload"]["timestamp_utc"])
        t1 = pd.Timestamp(rows[i + 1]["payload"]["timestamp_utc"])
        w = rows[i]["payload"]["target_weights"]
        seg = rets.loc[(rets.index > t0) & (rets.index <= t1)]
        for _, r in seg.iterrows():
            pr = sum(w.get(a, 0.0) * (r.get(a, 0.0) or 0.0) for a in universe)
            eq *= (1 + (pr if pr == pr else 0.0))
        curve.append((t1.isoformat(), round(eq, 8)))
    return curve


def main():
    if not PUBLIC.exists():
        print("no commits_public.csv yet")
        return 1
    rows = list(csv.DictReader(PUBLIC.open()))
    reveals = json.loads(REVEALS.read_text()) if REVEALS.exists() else None
    seed = chain.load_env().get("ATTEST_SALT_SEED", "").strip()
    mode = "independent (published reveals)" if reveals else "owner (seed recompute)"

    w3 = chain.get_w3()
    d = chain.deployment()
    c = w3.eth.contract(address=w3.to_checksum_address(d["address"]), abi=d["abi"])

    results, enriched = [], []
    for row in rows:
        ts = row["timestamp_utc"]
        cid = int(row["commit_id"])
        if reveals and str(cid) in reveals:
            salt = bytes.fromhex(reveals[str(cid)]["salt"][2:])
        elif seed:
            salt = deterministic_salt(seed, ts)
        else:
            print("FATAL: no reveals.json and no ATTEST_SALT_SEED")
            return 1
        onchain_hash, block_ts, revealed = c.functions.getCommit(cid).call()
        target = "0x" + onchain_hash.hex()
        # try each candidate spec; the one that reproduces the on-chain hash is the
        # spec that was frozen when this commit was made (handles the v1->v2 switch)
        payload, match = None, False
        for sp in SPECS:
            p = compute_signal(sp, ts)
            if ("0x" + commit_hash(p, salt).hex()) == target:
                payload, match = p, True
                break
        if payload is None:
            payload = compute_signal(SPECS[0], ts)  # for display only
        eff = pd.Timestamp(ts).timestamp()
        prompt = eff <= block_ts < eff + 3600
        results.append({"cid": cid, "ts": ts, "tx": row["tx"], "regime": payload["regime"],
                        "match": match, "prompt": prompt, "block_ts": block_ts,
                        "spec_version": payload.get("spec_version")})
        enriched.append({"payload": payload})

    matched = sum(r["match"] for r in results)
    prompt_n = sum(r["prompt"] for r in results)
    curve = forward_equity(enriched) if len(enriched) > 1 else []

    lines = [f"# On-Chain Attestation Verification", "",
             f"- Contract: [`{d['address']}`](https://bscscan.com/address/{d['address']}) (BSC mainnet)",
             f"- Verification mode: **{mode}**",
             f"- Commits: **{len(results)}** | hash matches: **{matched}/{len(results)}** | "
             f"prompt (committed within effective hour): **{prompt_n}/{len(results)}**", ""]
    if curve:
        lines.append(f"- Forward-test equity from revealed signals: **{curve[-1][1]:.4f}** "
                     f"(start 1.0000) over {len(curve)} hours")
        lines.append("")
    lines += ["| # | Effective hour (UTC) | Regime | Hash match | Prompt | Tx |",
              "|--:|----------------------|--------|:----------:|:------:|----|"]
    for r in results:
        lines.append(f"| {r['cid']} | {r['ts']} | {r['regime']} | "
                     f"{'✅' if r['match'] else '❌'} | {'✅' if r['prompt'] else '⚠️'} | "
                     f"[tx](https://bscscan.com/tx/{r['tx']}) |")
    OUT.write_text("\n".join(lines) + "\n")

    print(f"Verified {matched}/{len(results)} hashes match, {prompt_n}/{len(results)} prompt. -> {OUT}")
    return 0 if matched == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
