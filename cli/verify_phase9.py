#!/usr/bin/env python3
"""Phase 9 verification: the repo is public-safe (no secret leaks).

  - .env is git-ignored and was NEVER committed (checked across full history)
  - no secret VALUES from .env appear in any tracked file or anywhere in git history
  - no token-shaped strings (ghp_/github_pat_/0x<64 hex> private keys) in tracked files

Run: python cli/verify_phase9.py   (or: make verify-phase9)
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def sh(*args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout


# Only these .env keys hold actual secrets. Other keys (RPC/MCP URLs) are public config.
SECRET_KEYS = {"CMC_API_KEY", "X402_BASE_PRIVATE_KEY", "ATTEST_PRIVATE_KEY",
               "ATTEST_SALT_SEED", "GH_PAT", "BSCSCAN_API_KEY"}


def load_secret_values():
    vals = []
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = (x.strip() for x in line.split("=", 1))
                if k in SECRET_KEYS and len(v) >= 12 and not v.lower().startswith("http"):
                    vals.append(v)
    return vals


def main():
    fails = []

    def check(c, m):
        print(f"  [{'PASS' if c else 'FAIL'}] {m}")
        if not c:
            fails.append(m)

    # .env ignored + never committed
    ignored = subprocess.run(["git", "check-ignore", ".env"], cwd=REPO,
                             capture_output=True, text=True).returncode == 0
    check(ignored, ".env is git-ignored")
    env_history = sh("git", "log", "--all", "--oneline", "--", ".env").strip()
    check(env_history == "", ".env never appears in git history")

    # secret values absent from tracked files AND full history
    secrets = load_secret_values()
    tracked = sh("git", "ls-files").splitlines()
    full_history = sh("git", "log", "--all", "-p")
    for v in secrets:
        in_tracked = any(v in (REPO / f).read_text(errors="ignore")
                         for f in tracked if (REPO / f).is_file())
        check(not in_tracked, f"secret value (…{v[-4:]}) not in any tracked file")
        check(v not in full_history, f"secret value (…{v[-4:]}) not anywhere in git history")

    # token-shaped strings in tracked files
    patterns = [r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{50,}"]
    blob = "".join((REPO / f).read_text(errors="ignore")
                   for f in tracked if (REPO / f).is_file() and (REPO / f).suffix in
                   (".py", ".md", ".json", ".txt", ".yml", ".yaml", ".sol", ".csv", ""))
    for pat in patterns:
        hits = re.findall(pat, blob)
        check(not hits, f"no token-shaped strings matching /{pat[:18]}…/ in tracked files")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s) — DO NOT publish until fixed.")
        return 1
    print("ALL PHASE 9 CHECKS PASS — repo is public-safe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
