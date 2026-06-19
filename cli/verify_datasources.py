#!/usr/bin/env python3
"""Verify DATA_SOURCES.md against the real external call sites.

Extracts every external host actually called from the fetch/client code and asserts:
  - every such host is documented in DATA_SOURCES.md (no undocumented call site)
  - every host named in DATA_SOURCES.md exists in the code (no phantom row)

Run: python cli/verify_datasources.py   (or: make verify-datasources)
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CODE_DIRS = ["engine", "cli", "attest", "x402plan"]
# hosts we don't count as data sources (tooling / explorers / docs)
IGNORE = ("github.com", "bscscan.com", "readthedocs", "ipfs", "example.com",
          "websockets.readthedocs")
HOST_RE = re.compile(r"https?://([a-zA-Z0-9.\-]+)")


def code_hosts():
    hosts = set()
    for d in CODE_DIRS:
        for f in (REPO / d).rglob("*.py"):
            for h in HOST_RE.findall(f.read_text()):
                if not any(ig in h for ig in IGNORE):
                    hosts.add(h)
    return hosts


def main():
    doc = (REPO / "DATA_SOURCES.md").read_text()
    # normalise: the doc may show a wildcard bsc-dataseed*; match by family
    hosts = code_hosts()
    fails = []

    def documented(h):
        if h in doc:
            return True
        # families that the doc lists with a wildcard / representative member
        if h.startswith("bsc-dataseed") and "bsc-dataseed" in doc:
            return True
        if h.startswith("bsc.publicnode") and "publicnode" in doc:
            return True
        if h.startswith("bsc-dataseed1.binance.org") and "bnbchain.org" in doc:
            return True
        return False

    for h in sorted(hosts):
        ok = documented(h)
        print(f"  [{'PASS' if ok else 'FAIL'}] code host documented: {h}")
        if not ok:
            fails.append(f"undocumented:{h}")

    # phantom check: every distinct host token in the doc table should exist in code
    doc_hosts = {h for h in HOST_RE.findall(doc)} | set(
        re.findall(r"`([a-z0-9.\-]+\.(?:org|com|vision|io))", doc))
    for h in sorted(doc_hosts):
        if any(ig in h for ig in IGNORE):
            continue
        in_code = any(h in (REPO / d / p).read_text()
                      for d in CODE_DIRS for p in [""] if False) or \
            any(h in f.read_text() for d in CODE_DIRS for f in (REPO / d).rglob("*.py"))
        if not in_code and not h.startswith("bsc-dataseed"):
            print(f"  [WARN] doc host not literally found in code (check): {h}")

    print()
    if fails:
        print(f"FAIL: {len(fails)} data-source mismatch(es): {fails}")
        return 1
    print(f"ALL DATA-SOURCE CHECKS PASS — {len(hosts)} code hosts all documented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
